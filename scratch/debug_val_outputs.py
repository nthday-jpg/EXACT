import os
import sys
import torch
import json
import re

# Ensure project root is in path
from pathlib import Path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from src.logic.reasoning.parser import try_parse_fol

# paths
MODEL_ID = "d:/mduy/source/repos/EXACT/model_cache"
ADAPTER_DIR = "d:/mduy/source/repos/EXACT/results"
DATA_PATH = "d:/mduy/source/repos/EXACT/data/processed/logic_merged_valid_augmented.json"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

from transformers import BitsAndBytesConfig
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

# Load model
print("Loading model and adapter...")
base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, 
    quantization_config=quantization_config,
    device_map="auto"
)
model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
model.eval()

# Load dataset
with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

val_samples = [s for s in data if s.get("split") == "val"]
print(f"Total validation samples: {len(val_samples)}")

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

def clean_json_response(response: str) -> str:
    response = response.strip()
    if response.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            response = match.group(1).strip()
            
    first_brace = response.find("{")
    first_bracket = response.find("[")
    
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        obj_match = re.search(r"(\\{.*\\})", response, re.DOTALL)
        if obj_match:
            response = obj_match.group(1).strip()
        else:
            obj_match_open = re.search(r"(\\{.*)", response, re.DOTALL)
            if obj_match_open:
                response = obj_match_open.group(1).strip()
    elif first_bracket != -1:
        array_match = re.search(r"(\\[.*\\])", response, re.DOTALL)
        if array_match:
            response = array_match.group(1).strip()
        else:
            array_match_open = re.search(r"(\\[.*)", response, re.DOTALL)
            if array_match_open:
                response = array_match_open.group(1).strip()
                
    in_quote = False
    escape = False
    stack = []
    i = 0
    while i < len(response):
        char = response[i]
        if escape:
            escape = False
        elif char == '\\':
            escape = True
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote:
            if char in ('{', '['):
                stack.append(char)
            elif char in ('}', ']'):
                if stack and ((char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '[')):
                    stack.pop()
        i += 1
        
    if in_quote:
        response += '"'
    while stack:
        top = stack.pop()
        if top == '{':
            response += '}'
        elif top == '[':
            response += ']'
            
    return response

# Test generation on a few samples
for idx, item in enumerate(val_samples[:3]):
    print(f"\n====================== SAMPLE {idx+1} ======================")
    nl_list = item["premises-NL"]
    fol_list_gt = item["premises-FOL"]
    
    nl_content = ""
    for i, nl in enumerate(nl_list, start=1):
        nl_content += f"{i}. {nl}\n"
        
    user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
    messages = [
        {"role": "system", "content": system_prompt_template},
        {"role": "user", "content": user_prompt.strip()}
    ]
    
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
        
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    print("RAW RESPONSE:")
    print(response)
    print("----------------------------------------")
    
    cleaned = clean_json_response(response)
    print("CLEANED RESPONSE:")
    print(cleaned)
    print("----------------------------------------")
    
    try:
        parsed = json.loads(cleaned)
        print("PARSED SUCCESSFUL! List length:", len(parsed))
        print("GROUND TRUTH length:", len(fol_list_gt))
        
        # Test try_parse_fol on each generated formula
        for f_idx, formula in enumerate(parsed):
            is_valid, err = try_parse_fol(str(formula))
            print(f"Formula {f_idx+1}: {formula}")
            print(f"  Valid: {is_valid} | Error: {err}")
            
            # Print corresponding GT formula
            if f_idx < len(fol_list_gt):
                print(f"  GT formula: {fol_list_gt[f_idx]}")
                is_gt_valid, gt_err = try_parse_fol(str(fol_list_gt[f_idx]))
                print(f"  GT Valid: {is_gt_valid} | GT Error: {gt_err}")
                print(f"  Direct String Match: {str(formula).strip() == str(fol_list_gt[f_idx]).strip()}")
    except Exception as e:
        print("PARSED FAILED:", e)
