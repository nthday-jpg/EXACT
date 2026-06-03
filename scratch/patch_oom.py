import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

if not os.path.exists(notebook_path):
    print(f"Error: Notebook not found at {notebook_path}")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

old_target = """    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        task_ids = inputs.pop("task_id", None)
        outputs = model(**inputs)
        
        logits = outputs.logits
        labels = inputs.get("labels")
        
        if labels is None or task_ids is None:
            loss = outputs.loss if isinstance(outputs, dict) else outputs[0]
            return (loss, outputs) if return_outputs else loss
            
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        loss_fct = torch.nn.CrossEntropyLoss(reduction="none")
        batch_size = shift_logits.size(0)
        vocab_size = shift_logits.size(-1)
        
        per_token_loss = loss_fct(shift_logits.view(-1, vocab_size), shift_labels.view(-1))
        per_token_loss = per_token_loss.view(batch_size, -1)
        
        valid_mask = (shift_labels != -100).float()
        masked_loss = per_token_loss * valid_mask
        
        sample_losses = masked_loss.sum(dim=-1)
        sample_tokens = valid_mask.sum(dim=-1)
        sample_tokens = torch.clamp(sample_tokens, min=1.0)
        sample_mean_losses = sample_losses / sample_tokens"""

new_target = """    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        task_ids = inputs.pop("task_id", None)
        outputs = model(**inputs)
        
        logits = outputs.logits
        labels = inputs.get("labels")
        
        if labels is None or task_ids is None:
            loss = outputs.loss if isinstance(outputs, dict) else outputs[0]
            return (loss, outputs) if return_outputs else loss
            
        shift_logits = logits[..., :-1, :]
        shift_labels = labels[..., 1:]
        
        loss_fct = torch.nn.CrossEntropyLoss(reduction="none")
        batch_size = shift_logits.size(0)
        
        # Highly optimized, memory-efficient loss calculation to prevent CUDA OOM
        # Only compute cross entropy on active tokens (where label != -100)
        per_token_loss = torch.zeros_like(shift_labels, dtype=logits.dtype)
        active_mask = (shift_labels != -100)
        
        if active_mask.any():
            active_logits = shift_logits[active_mask]
            active_labels = shift_labels[active_mask]
            active_loss = loss_fct(active_logits, active_labels)
            per_token_loss[active_mask] = active_loss.to(logits.dtype)
            
        valid_mask = active_mask.float()
        masked_loss = per_token_loss * valid_mask
        
        sample_losses = masked_loss.sum(dim=-1)
        sample_tokens = valid_mask.sum(dim=-1)
        sample_tokens = torch.clamp(sample_tokens, min=1.0)
        sample_mean_losses = sample_losses / sample_tokens"""

patched = False
for cell in nb.get("cells", []):
    source = cell.get("source", [])
    if not source:
        continue
    source_str = "".join(source)
    if "def compute_loss(self, model, inputs, return_outputs=False, **kwargs):" in source_str:
        # Standardize carriage returns
        source_str_norm = source_str.replace("\r\n", "\n")
        old_target_norm = old_target.replace("\r\n", "\n")
        new_target_norm = new_target.replace("\r\n", "\n")
        
        if old_target_norm in source_str_norm:
            patched_str = source_str_norm.replace(old_target_norm, new_target_norm)
            # Split back into lines, keeping newlines
            patched_lines = [line + "\n" for line in patched_str.split("\n")]
            # Clean up the last element if it's just an empty newline
            if patched_lines and patched_lines[-1] == "\n":
                patched_lines.pop()
            cell["source"] = patched_lines
            patched = True
            break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook patched successfully with optimized compute_loss!")
else:
    print("Failed to find exact old target string in notebook cell 6. Maybe it's already modified?")
