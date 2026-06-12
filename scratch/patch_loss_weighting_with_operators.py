import json
import os
import re
from pathlib import Path

def patch_notebook(nb_path, target_class_def, replacement_class_def):
    if not os.path.exists(nb_path):
        print(f"Warning: Notebook {nb_path} not found.")
        return False
        
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    updated = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            source_text = "".join(cell.get("source", []))
            if "class CustomSFTTrainer(SFTTrainer):" in source_text:
                start_idx = source_text.find("class CustomSFTTrainer(SFTTrainer):")
                end_token = "return (loss, outputs) if return_outputs else loss"
                end_idx = source_text.find(end_token, start_idx)
                if end_idx != -1:
                    actual_end = end_idx + len(end_token)
                    while actual_end < len(source_text) and source_text[actual_end] in ['\n', '\r', ' ']:
                        actual_end += 1
                        
                    new_source_text = source_text[:start_idx] + replacement_class_def + source_text[actual_end:]
                    cell["source"] = [line + "\n" for line in new_source_text.splitlines()]
                    if cell["source"] and cell["source"][-1] == "\n":
                        cell["source"].pop()
                    updated = True
                    break
                    
    if updated:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully patched notebook: {nb_path}")
    else:
        print(f"Failed to find CustomSFTTrainer cell in notebook: {nb_path}")
    return updated

def patch_fol_notebook_from_scratch(nb_path, new_class_def):
    if not os.path.exists(nb_path):
        print(f"Warning: Notebook {nb_path} not found.")
        return False
        
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    updated = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            source_text = "".join(cell.get("source", []))
            if "def train_model(train_dataset, val_dataset, val_samples, output_dir):" in source_text:
                idx = source_text.find("def train_model(train_dataset, val_dataset, val_samples, output_dir):")
                
                old_trainer = "trainer = SFTTrainer("
                new_trainer = "trainer = CustomSFTTrainer("
                
                new_source_text = source_text[:idx] + new_class_def + "\n\n" + source_text[idx:]
                new_source_text = new_source_text.replace(old_trainer, new_trainer, 1)
                
                cell["source"] = [line + "\n" for line in new_source_text.splitlines()]
                if cell["source"] and cell["source"][-1] == "\n":
                    cell["source"].pop()
                updated = True
                break
                
    if updated:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully patched fol.ipynb from scratch: {nb_path}")
    else:
        print(f"Failed to find train_model cell in fol.ipynb: {nb_path}")
    return updated

def patch_generator_script(script_path, replacement_class_def):
    if not os.path.exists(script_path):
        print(f"Warning: Generator script {script_path} not found.")
        return False
        
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    start_idx = content.find("class CustomSFTTrainer(SFTTrainer):")
    if start_idx == -1:
        print(f"Failed to find CustomSFTTrainer in script: {script_path}")
        return False
        
    end_token = "return (loss, outputs) if return_outputs else loss"
    end_idx = content.find(end_token, start_idx)
    if end_idx == -1:
        print(f"Failed to find end of CustomSFTTrainer in script: {script_path}")
        return False
        
    actual_end = end_idx + len(end_token)
    pattern = re.compile(r"class CustomSFTTrainer\(SFTTrainer\):.*?return \(loss, outputs\) if return_outputs else loss", re.DOTALL)
    formatted_replacement = replacement_class_def.replace('\\n', '\\\\n').replace('\\t', '\\\\t')
    
    new_content, count = pattern.subn(formatted_replacement, content)
    if count > 0:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully patched generator script: {script_path} (replaced {count} matches)")
        return True
    else:
        print(f"Regex replacement failed for script: {script_path}")
        return False

def main():
    root = Path(__file__).resolve().parents[1]
    
    # The new CustomSFTTrainer implementation
    new_class_def = """class CustomSFTTrainer(SFTTrainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        \"\"\"
        Custom loss computation to apply task-specific and token-specific loss weighting.
        Task classification: FOL (system prompt prefix [2610, 5508]) vs other tasks.
        Inside FOL, we weight rare logical operators (Exists, OR, <->, !=) higher to combat imbalance.
        \"\"\"
        if "labels" not in inputs:
            return super().compute_loss(model, inputs, return_outputs, **kwargs)
            
        labels = inputs["labels"]
        input_ids = inputs["input_ids"]
        outputs = model(**inputs)
        logits = outputs.get("logits")
        
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss_fct = nn.CrossEntropyLoss(reduction="none")
        
        vocab_size = shift_logits.size(-1)
        flat_logits = shift_logits.view(-1, vocab_size)
        flat_labels = shift_labels.view(-1)
        
        token_losses = loss_fct(flat_logits, flat_labels)
        token_losses = token_losses.view(shift_labels.size())
        
        # Determine rare logical operator token IDs dynamically from processing_class/tokenizer
        tokenizer = self.processing_class if hasattr(self, 'processing_class') else getattr(self, 'tokenizer', None)
        logic_tokens = ["Exists", "OR", "<->", "!=", "Exists(x", "Exists(y", "Exists(z"]
        logic_token_ids = set()
        if tokenizer is not None:
            for tok in logic_tokens:
                ids = tokenizer.encode(tok, add_special_tokens=False)
                logic_token_ids.update(ids)
                logic_token_ids.update(tokenizer.encode(tok.lower(), add_special_tokens=False))
                logic_token_ids.update(tokenizer.encode(tok.upper(), add_special_tokens=False))
        
        weighted_losses = []
        for i in range(input_ids.size(0)):
            seq_input_ids = input_ids[i].tolist()
            seq_losses = token_losses[i]
            seq_labels = shift_labels[i]
            
            is_fol = False
            for idx in range(len(seq_input_ids) - 5):
                if idx > 20:
                    break
                if seq_input_ids[idx] == 2610 and seq_input_ids[idx+1] == 5508:
                    is_fol = True
                    break
            
            # If the dataset has only FOL samples (e.g. training only on fol.ipynb), is_fol is True
            # Let's check if there are no physics tokens, or fallback to True if the file name is fol SFT
            if not is_fol and len(seq_input_ids) > 0:
                # If we're inside fol.ipynb SFT, all samples are FOL
                is_fol = True
            
            valid_mask = (seq_labels != -100)
            active_losses = seq_losses[valid_mask]
            active_labels = seq_labels[valid_mask]
            
            if len(active_losses) > 0:
                mean_loss = active_losses.mean()
                
                # Apply token weighting for rare logical operators in FOL SFT targets
                if is_fol and len(logic_token_ids) > 0:
                    token_weights = torch.ones_like(active_losses)
                    for j, lbl in enumerate(active_labels.tolist()):
                        if lbl in logic_token_ids:
                            token_weights[j] = 5.0  # Apply 5x weight to rare operators
                    mean_loss = (active_losses * token_weights).mean()
                
                weight = 3.0 if is_fol else 1.0
                weighted_losses.append(mean_loss * weight)
            else:
                weighted_losses.append(torch.tensor(0.0, device=logits.device, dtype=logits.dtype))
                
        loss = torch.stack(weighted_losses).mean()
        return (loss, outputs) if return_outputs else loss"""

    # 1. Patch fol_and_physics.ipynb
    nb_phys = root / "src" / "llm" / "tuning" / "fol_and_physics.ipynb"
    patch_notebook(nb_phys, "class CustomSFTTrainer(SFTTrainer):", new_class_def)
    
    # 2. Patch fol_and_router.ipynb
    nb_router = root / "src" / "llm" / "tuning" / "fol_and_router.ipynb"
    patch_notebook(nb_router, "class CustomSFTTrainer(SFTTrainer):", new_class_def)
    
    # 3. Patch fol.ipynb
    nb_fol = root / "src" / "llm" / "tuning" / "fol.ipynb"
    # Try updating CustomSFTTrainer if it exists, otherwise do from scratch
    if not patch_notebook(nb_fol, "class CustomSFTTrainer(SFTTrainer):", new_class_def):
        patch_fol_notebook_from_scratch(nb_fol, new_class_def)
    
    # 4. Patch generate_fol_and_router_notebook.py
    gen_script = root / "scratch" / "generate_fol_and_router_notebook.py"
    patch_generator_script(gen_script, new_class_def)

if __name__ == "__main__":
    main()
