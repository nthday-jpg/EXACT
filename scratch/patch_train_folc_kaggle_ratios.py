import json
import os

def main():
    notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    print(f"Loaded notebook with {len(nb['cells'])} cells.")
    
    # Helper to convert multiline string to list of lines with trailing newlines
    def to_cell_source(text):
        lines = text.splitlines()
        source = [line + "\n" for line in lines]
        # Remove trailing newline from the very last line to match Jupyter style
        if source and source[-1].endswith("\n"):
            source[-1] = source[-1][:-1]
        return source

    # Cell 5: Dataset split and formatting
    cell5_text = """# 5. Format Dataset (Chat Template) and split Train/Val
import os
import json
import random
from datasets import Dataset

# Define prompt templates for flat JSON list output with strict count constraint
system_prompt_template = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\\n\\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\\n"
    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\\n\\n"
    "ALLOWED OPERATORS:\\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\\n\\n"
    "QUANTIFIER RULES:\\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\\n\\n"
    "Return JSON only."
)

user_prompt_template = (
    "Convert the following {num_premises} premises into canonical first-order logic.\\n\\n"
    "Premises:\\n"
    "{premises}\\n\\n"
    "Return a JSON list of exactly {num_premises} strings containing the formulas, in the exact same order."
)

# --- Split FOL dataset before augmentation to prevent data leakage ---
has_presplit = all("split" in sample for sample in raw_samples)
if has_presplit:
    train_fol = [s for s in raw_samples if s.get("split") == "train"]
    val_fol = [s for s in raw_samples if s.get("split") == "val"]
    # Track statistics for print compatibility below
    train_orig_fol = [s for s in train_fol if "augmented" not in str(s.get("dataset_source", ""))]
    val_orig_fol = val_fol
    train_augmented_fol = [s for s in train_fol if "augmented" in str(s.get("dataset_source", ""))]
else:
    original_fol = []
    augmented_fol = []
    for sample in raw_samples:
        ds = str(sample.get("dataset_source", ""))
        if "augmented" in ds:
            augmented_fol.append(sample)
        else:
            original_fol.append(sample)

    # Shuffle original FOL samples deterministically
    random.Random(42).shuffle(original_fol)
    split_idx_fol = int(len(original_fol) * 0.9)
    train_orig_fol = original_fol[:split_idx_fol]
    val_orig_fol = original_fol[split_idx_fol:]

    # Map augmented samples back to train split
    train_orig_ids = set(x["example_id"] for x in train_orig_fol)

    def get_original_id(example_id):
        for suffix in ["_aug_var", "_perm_var", "_neg_var"]:
            if suffix in example_id:
                return example_id.split(suffix)[0]
        return example_id

    train_augmented_fol = []
    for sample in augmented_fol:
        base_id = get_original_id(sample["example_id"])
        if base_id in train_orig_ids:
            train_augmented_fol.append(sample)

    # Combine splits
    train_fol = train_orig_fol + train_augmented_fol
    val_fol = val_orig_fol

# --- Split Physics dataset deterministically ---
random.Random(42).shuffle(physics_samples)
split_idx_phys = int(len(physics_samples) * 0.9)
train_physics = physics_samples[:split_idx_phys]
val_physics = physics_samples[split_idx_phys:]

# --- Format training and validation samples ---
def format_samples(fol_list, physics_list, balance_oversample=False):
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

def apply_template(batch):
    texts = []
    for messages in batch["messages"]:
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {"text": texts}

# --- PREPARE VAL DATASET (Common for both phases) ---
formatted_val = format_samples(val_fol, val_physics, balance_oversample=False)
val_dataset = Dataset.from_list(formatted_val)
val_dataset = val_dataset.map(apply_template, batched=True, remove_columns=["messages"])
val_dataset = val_dataset.shuffle(seed=42)

# --- PREPARE DATASETS FOR PHASE 1 ---
# FOL: 100%, Physics: 20%
# Select a deterministic 20% slice of train_physics
num_phys_p1 = int(len(train_physics) * 0.20)
train_physics_p1 = train_physics[:num_phys_p1]

formatted_train_p1 = format_samples(train_fol, train_physics_p1, balance_oversample=False)
train_dataset_p1 = Dataset.from_list(formatted_train_p1)
train_dataset_p1 = train_dataset_p1.map(apply_template, batched=True, remove_columns=["messages"])
train_dataset_p1 = train_dataset_p1.shuffle(seed=42)

# --- PREPARE DATASETS FOR PHASE 2 ---
# Physics: 100%, FOL: 50%
# Select a deterministic 50% slice of train_fol
num_fol_p2 = int(len(train_fol) * 0.50)
train_fol_p2 = random.Random(42).sample(train_fol, num_fol_p2)

formatted_train_p2 = format_samples(train_fol_p2, train_physics, balance_oversample=False)
train_dataset_p2 = Dataset.from_list(formatted_train_p2)
train_dataset_p2 = train_dataset_p2.map(apply_template, batched=True, remove_columns=["messages"])
train_dataset_p2 = train_dataset_p2.shuffle(seed=42)

print(f"FOL Train/Val Split: original train={len(train_orig_fol)}, original val={len(val_orig_fol)}")
print(f"FOL Augmented added to Train: {len(train_augmented_fol)}")
print(f"Physics Train/Val Split: train={len(train_physics)}, val={len(val_physics)}")
print(f"Common Validation size: {len(val_dataset)}")
print(f"Phase 1 - Train size (100% FOL : 20% Physics): {len(train_dataset_p1)}")
print(f"Phase 2 - Train size (100% Physics : 50% FOL): {len(train_dataset_p2)}")"""

    # Cell 7: Start Training and Post-Training Evaluation
    cell7_text = """# 7. Start Training and Post-Training Evaluation (2-Phase Strategy)
print("=== STARTING PHASE 1 (FOL focus: 100% FOL : 20% Physics) ===")
train_model(
    train_dataset=train_dataset_p1,
    val_dataset=val_dataset,
    output_dir=OUTPUT_DIR_P1,
    epochs=EPOCHS_P1,
    learning_rate=LEARNING_RATE_P1,
    resume_from_dir=None
)

print("\\n=== STARTING PHASE 2 (Physics focus: 100% Physics : 50% FOL) ===")
train_model(
    train_dataset=train_dataset_p2,
    val_dataset=val_dataset,
    output_dir=OUTPUT_DIR_P2,
    epochs=EPOCHS_P2,
    learning_rate=LEARNING_RATE_P2,
    resume_from_dir=OUTPUT_DIR_P1
)"""

    # Apply changes
    found_5 = False
    found_7 = False
    
    for cell in nb['cells']:
        if cell.get('cell_type') == 'code':
            source_str = "".join(cell['source'])
            if "# 5. Format Dataset" in source_str:
                cell['source'] = to_cell_source(cell5_text)
                found_5 = True
                print("Patched Cell 5 (optimized ratios)")
            elif "# 7. Start Training" in source_str:
                cell['source'] = to_cell_source(cell7_text)
                found_7 = True
                print("Patched Cell 7 (Execution with common validation and Phase 2 ratios)")
                
    if found_5 and found_7:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print("Successfully updated notebook with optimized ratios!")
    else:
        print(f"Error: Could not find all cells (found: Cell 5={found_5}, Cell 7={found_7})")

if __name__ == '__main__':
    main()
