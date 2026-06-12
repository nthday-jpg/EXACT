import os
import json
import random
import sys

# Add repo root to path if needed
sys.path.append("d:/mduy/source/repos/EXACT")

def test_dry_run():
    print("=== STARTING DRY RUN VALIDATION ===")
    
    # 1. Test imports and basic configurations
    print("Testing imports...")
    try:
        import torch
        from transformers import AutoTokenizer, DataCollatorForLanguageModeling
        from datasets import Dataset
        from trl import SFTTrainer, SFTConfig
        from peft import LoraConfig
        import sympy as sp
        print("Imports successful!")
    except Exception as e:
        print(f"Error during import test: {e}")
        sys.exit(1)
        
    # 2. Paths
    MODEL_ID = "d:/mduy/source/repos/EXACT/model_cache"
    PHYSICS_PATH = "d:/mduy/source/repos/EXACT/data/processed/physics_distillation.json"
    ROUTER_PATH = "d:/mduy/source/repos/EXACT/data/processed/router_dataset.json"
    
    # 3. Load Datasets
    print("\nLoading datasets...")
    with open(PHYSICS_PATH, "r", encoding="utf-8") as f:
        phys_data = json.load(f)[:5] # Load 5 samples
    with open(ROUTER_PATH, "r", encoding="utf-8") as f:
        router_data = json.load(f)[:5] # Load 5 samples
    print(f"Loaded {len(phys_data)} physics and {len(router_data)} router validation samples.")
    
    # 4. Tokenizer
    print("\nInitializing tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print("Tokenizer loaded successfully!")
    
    # 5. Prompts definitions (we copy the prompts from the notebook cells to test format compatibility)
    from scratch.analyze_datasets import physics_system_prompt, router_system_prompt
    
    # 6. Format Samples
    def format_samples(physics_list, router_list):
        formatted = []
        for item in physics_list:
            inp = item["input"]
            out = item["output"]
            formatted.append({
                "messages": [
                    {"role": "system", "content": physics_system_prompt},
                    {"role": "user", "content": inp.strip()},
                    {"role": "assistant", "content": out.strip()}
                ]
            })
        for item in router_list:
            inp = item["input"]
            out = item["output"]
            formatted.append({
                "messages": [
                    {"role": "system", "content": router_system_prompt},
                    {"role": "user", "content": f"<QUESTION>\n{inp.strip()}\n</QUESTION>"},
                    {"role": "assistant", "content": out.strip()}
                ]
            })
        return formatted

    def apply_template(batch):
        texts = []
        for messages in batch["messages"]:
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}

    print("\nFormatting samples...")
    formatted_val = format_samples(phys_data, router_data)
    val_dataset = Dataset.from_list(formatted_val)
    val_dataset = val_dataset.map(apply_template, batched=True, remove_columns=["messages"])
    
    print(f"Dataset mapping complete. Total verification samples: {len(val_dataset)}")
    
    # Let's inspect the first element of physics and first of router
    print("\nSample 1 (Physics) text prefix:")
    print(val_dataset[0]["text"][:300] + "...")
    print("\nSample 6 (Router) text prefix:")
    print(val_dataset[5]["text"][:300] + "...")
    
    # 7. Test custom collator
    print("\nTesting Custom Data Collator...")
    class CustomDataCollator(DataCollatorForLanguageModeling):
        def __init__(self, response_template, tokenizer, *args, **kwargs):
            super().__init__(tokenizer=tokenizer, mlm=False, *args, **kwargs)
            self.response_template = response_template
            self.response_token_ids = self.tokenizer.encode(self.response_template, add_special_tokens=False)
            
        def __call__(self, examples):
            batch = super().__call__(examples)
            labels = batch["labels"]
            for i in range(labels.size(0)):
                input_ids = batch["input_ids"][i].tolist()
                response_idx = -1
                n_template = len(self.response_token_ids)
                for j in range(len(input_ids) - n_template + 1):
                    if input_ids[j:j+n_template] == self.response_token_ids:
                        response_idx = j + n_template
                        break
                if response_idx != -1:
                    labels[i, :response_idx] = -100
            return batch

    response_template = "<|im_start|>assistant\n"
    collator = CustomDataCollator(response_template=response_template, tokenizer=tokenizer)
    
    # Tokenize two samples for collator test
    tokenized_examples = []
    for item in val_dataset:
        inputs = tokenizer(item["text"])
        tokenized_examples.append(inputs)
        
    collator_batch = collator(tokenized_examples)
    labels = collator_batch["labels"]
    
    # Verify labels weighting mask (-100 is ignored index)
    print("Collator test verification:")
    for idx, (lbl, inp_id) in enumerate(zip(labels[0].tolist(), collator_batch["input_ids"][0].tolist())):
        # Check first token that is NOT -100
        if lbl != -100:
            print(f"  First non-masked label at index {idx}. Decoded token: '{tokenizer.decode([lbl])}' (Expected assistant response start)")
            break
            
    print("\n=== DRY RUN VALIDATION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_dry_run()
