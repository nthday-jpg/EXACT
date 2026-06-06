import os
import json
import numpy as np
from transformers import AutoTokenizer

# Paths
MODEL_DIR = r"d:\mduy\source\repos\EXACT\model_cache"
PHYSICS_PATH = r"d:\mduy\source\repos\EXACT\data\processed\physics_distillation.json"
LOGIC_PATH = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True, local_files_only=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# -----------------
# 1. Physics Data
# -----------------
SOLVER_PATH = r"d:\mduy\source\repos\EXACT\src\physics\instructions\solver.md"
with open(SOLVER_PATH, "r", encoding="utf-8") as f:
    physics_system_prompt = f.read().strip()

def analyze_physics_tokens():
    print("Analyzing Physics Dataset...")
    with open(PHYSICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    total_lens = []
    prompt_lens = []
    response_lens = []
    
    for item in data:
        inp = item.get("input", "")
        out = item.get("output", "")
        if not inp or not out:
            continue
            
        messages = [
            {"role": "system", "content": physics_system_prompt},
            {"role": "user", "content": inp.strip()},
            {"role": "assistant", "content": out.strip()}
        ]
        
        # Total tokens
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        total_tokens = len(tokenizer.encode(text))
        
        # Prompt tokens (system + user)
        prompt_messages = [
            {"role": "system", "content": physics_system_prompt},
            {"role": "user", "content": inp.strip()}
        ]
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        prompt_tokens = len(tokenizer.encode(prompt_text))
        
        total_lens.append(total_tokens)
        prompt_lens.append(prompt_tokens)
        response_lens.append(total_tokens - prompt_tokens)
        
    print_stats("Physics (Total Sequence)", total_lens)
    print_stats("Physics (Prompt Only)", prompt_lens)
    print_stats("Physics (Response Only)", response_lens)
    print("-" * 50)

# -----------------
# 2. Logic/FOL Data
# -----------------
system_prompt_template = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n"
    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\n\n"
    "ALLOWED OPERATORS:\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
    "QUANTIFIER RULES:\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
    "Return JSON only."
)

user_prompt_template = (
    "Convert the following {num_premises} premises into canonical first-order logic.\n\n"
    "Premises:\n"
    "{premises}\n\n"
    "Return a JSON list of exactly {num_premises} strings containing the formulas, in the exact same order."
)

def analyze_logic_tokens():
    print("Analyzing Logic (FOL) Dataset...")
    with open(LOGIC_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    total_lens = []
    prompt_lens = []
    response_lens = []
    
    for item in data:
        nl_list = item.get("premises-NL", [])
        fol_list = item.get("premises-FOL", [])
        if not nl_list or not fol_list or len(nl_list) != len(fol_list):
            continue
            
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\n"
            
        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        assistant_response = json.dumps(fol_list, indent=2)
        
        messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt.strip()},
            {"role": "assistant", "content": assistant_response.strip()}
        ]
        
        # Total tokens
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        total_tokens = len(tokenizer.encode(text))
        
        # Prompt tokens
        prompt_messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt.strip()}
        ]
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        prompt_tokens = len(tokenizer.encode(prompt_text))
        
        total_lens.append(total_tokens)
        prompt_lens.append(prompt_tokens)
        response_lens.append(total_tokens - prompt_tokens)
        
    print_stats("Logic (Total Sequence)", total_lens)
    print_stats("Logic (Prompt Only)", prompt_lens)
    print_stats("Logic (Response Only)", response_lens)
    print("-" * 50)

def print_stats(name, values):
    if not values:
        print(f"{name}: Empty")
        return
    values = np.array(values)
    print(f"{name}:")
    print(f"  Count:  {len(values)}")
    print(f"  Mean:   {np.mean(values):.1f}")
    print(f"  Min:    {np.min(values)}")
    print(f"  Median: {np.median(values):.1f}")
    print(f"  90th %: {np.percentile(values, 90):.1f}")
    print(f"  95th %: {np.percentile(values, 95):.1f}")
    print(f"  98th %: {np.percentile(values, 98):.1f}")
    print(f"  99th %: {np.percentile(values, 99):.1f}")
    print(f"  Max:    {np.max(values)}")

if __name__ == "__main__":
    analyze_physics_tokens()
    analyze_logic_tokens()
