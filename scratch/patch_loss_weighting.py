import json
import os

def main():
    notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    print(f"Loaded notebook with {len(nb['cells'])} cells.")
    
    # ---------------------------------------------
    # 1. Update Cell 5 (Dataset split and formatting)
    # ---------------------------------------------
    found_5 = False
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code' and cell.get('id') == '2712f8d5':
            found_5 = True
            source_text = "".join(cell['source'])
            
            # Locate format_samples function
            start_func_idx = source_text.find("def format_samples(fol_list, physics_list):")
            end_func_idx = source_text.find("formatted_train = format_samples(train_fol, train_physics)")
            
            if start_func_idx == -1 or end_func_idx == -1:
                print("Error: Could not find format_samples function boundaries in Cell 5.")
                return
                
            new_func_text = """def format_samples(fol_list, physics_list, balance_oversample=False):
    formatted = []
    
    fol_samples = []
    # Format FOL translation samples
    for item in fol_list:
        nl_list = item["premises-NL"]
        fol_list_item = item["premises-FOL"]
        
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\\n"
            
        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        assistant_response = json.dumps(fol_list_item, indent=2)
        
        fol_samples.append({
            "messages": [
                {"role": "system", "content": system_prompt_template},
                {"role": "user", "content": user_prompt.strip()},
                {"role": "assistant", "content": assistant_response.strip()}
            ]
        })
        
    physics_samples_formatted = []
    # Format Physics samples
    for item in physics_list:
        physics_input = item["input"]
        physics_output = item["output"]
        
        physics_samples_formatted.append({
            "messages": [
                {"role": "system", "content": physics_system_prompt},
                {"role": "user", "content": physics_input.strip()},
                {"role": "assistant", "content": physics_output.strip()}
            ]
        })
        
    if balance_oversample:
        # Task-Balanced Batch sampling: Oversample FOL samples so that it matches Physics size
        # Shuffling them together ensures each batch has a balanced task mixture (close to 50/50)
        target_len = max(len(fol_samples), len(physics_samples_formatted))
        print(f"Balancing datasets via oversampling: target size = {target_len}")
        
        if len(fol_samples) < target_len:
            extra_needed = target_len - len(fol_samples)
            fol_samples += random.Random(42).choices(fol_samples, k=extra_needed)
        if len(physics_samples_formatted) < target_len:
            extra_needed = target_len - len(physics_samples_formatted)
            physics_samples_formatted += random.Random(42).choices(physics_samples_formatted, k=extra_needed)
            
    formatted = fol_samples + physics_samples_formatted
    return formatted

"""
            
            # Replace the old function text
            updated_source = source_text[:start_func_idx] + new_func_text
            
            # Also replace the formatting calls at the end
            calls_old = """formatted_train = format_samples(train_fol, train_physics)
formatted_val = format_samples(val_fol, val_physics)"""
            
            calls_new = """formatted_train = format_samples(train_fol, train_physics, balance_oversample=True)
formatted_val = format_samples(val_fol, val_physics, balance_oversample=False)"""
            
            rest_of_source = source_text[end_func_idx:]
            rest_of_source = rest_of_source.replace(calls_old, calls_new, 1)
            
            updated_source += rest_of_source
            
            # Convert back to list of lines ending in \n
            cell['source'] = [line + "\n" for line in updated_source.splitlines()]
            # Pop off any trailing newline from splitlines if necessary
            if cell['source'] and cell['source'][-1] == "\n":
                cell['source'].pop()
            print("Patched Cell 5 source text.")
            break
            
    if not found_5:
        print("Error: Cell 5 not found in notebook.")
        return

    # ---------------------------------------------
    # 2. Update Cell 6 (Configure Custom Trainer for Loss Weighting)
    # ---------------------------------------------
    found_6 = False
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code' and cell.get('id') == '0ece368f':
            found_6 = True
            source_text = "".join(cell['source'])
            
            # Find where def train_model starts
            train_model_idx = source_text.find("def train_model(train_dataset, val_dataset, output_dir):")
            if train_model_idx == -1:
                print("Error: Could not find train_model start in Cell 6.")
                return
                
            custom_trainer_class = """import torch.nn as nn

class CustomSFTTrainer(SFTTrainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        \"\"\"
        Custom loss computation to apply task-specific loss weighting.
        Task classification: FOL (system prompt prefix [2610, 5508]) vs Physics (prefix [2610, 525]).
        \"\"\"
        if "labels" not in inputs:
            return super().compute_loss(model, inputs, return_outputs, **kwargs)
            
        # Extract labels and inputs
        labels = inputs["labels"]
        input_ids = inputs["input_ids"]
        
        # We call the model to get logits
        outputs = model(**inputs)
        logits = outputs.get("logits")
        
        # Shift logits and labels for causal LM loss calculation
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        # Set up loss function with reduction='none' so we can weight per sequence
        loss_fct = nn.CrossEntropyLoss(reduction="none")
        
        # Flatten logits and labels
        vocab_size = shift_logits.size(-1)
        flat_logits = shift_logits.view(-1, vocab_size)
        flat_labels = shift_labels.view(-1)
        
        # Compute token-level losses
        token_losses = loss_fct(flat_logits, flat_labels)
        token_losses = token_losses.view(shift_labels.size())
        
        # Apply sequence-level loss weighting based on task type
        # We detect the task by checking the system prompt token sequence in input_ids
        weighted_losses = []
        for i in range(input_ids.size(0)):
            seq_input_ids = input_ids[i].tolist()
            seq_losses = token_losses[i]
            seq_labels = shift_labels[i]
            
            # Detect if it's FOL task
            # Prefix check: FOL starts system prompt with 'You convert' (tokens [2610, 5508])
            is_fol = False
            for idx in range(len(seq_input_ids) - 5):
                # Search within first 20 tokens to find system prompt prefix
                if idx > 20:
                    break
                if seq_input_ids[idx] == 2610 and seq_input_ids[idx+1] == 5508:
                    is_fol = True
                    break
            
            # Mask out non-active label tokens (-100)
            valid_mask = (seq_labels != -100)
            active_losses = seq_losses[valid_mask]
            
            if len(active_losses) > 0:
                mean_loss = active_losses.mean()
                # Physics response has ~10x more tokens than FOL. We weight FOL loss higher to compensate.
                # FOL loss weight = 3.0, Physics loss weight = 1.0
                weight = 3.0 if is_fol else 1.0
                weighted_losses.append(mean_loss * weight)
            else:
                weighted_losses.append(torch.tensor(0.0, device=logits.device, dtype=logits.dtype))
                
        loss = torch.stack(weighted_losses).mean()
        
        return (loss, outputs) if return_outputs else loss

"""
            
            # Insert CustomSFTTrainer right before train_model
            updated_source = source_text[:train_model_idx] + custom_trainer_class + source_text[train_model_idx:]
            
            # Replace SFTTrainer with CustomSFTTrainer in train_model
            old_trainer_instantiation = """    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        args=sft_config,
        data_collator=collator,
        callbacks=[LossLoggingCallback()]
    )"""
    
            new_trainer_instantiation = """    trainer = CustomSFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        args=sft_config,
        data_collator=collator,
        callbacks=[LossLoggingCallback()]
    )"""
            
            updated_source = updated_source.replace(old_trainer_instantiation, new_trainer_instantiation, 1)
            
            # Convert back to list of lines ending in \n
            cell['source'] = [line + "\n" for line in updated_source.splitlines()]
            # Pop off trailing newline if necessary
            if cell['source'] and cell['source'][-1] == "\n":
                cell['source'].pop()
            print("Patched Cell 6 source text.")
            break

    if not found_6:
        print("Error: Cell 6 not found in notebook.")
        return
        
    # Save notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Successfully saved notebook!")

if __name__ == '__main__':
    main()
