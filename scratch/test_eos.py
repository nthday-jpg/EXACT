import sys
import torch
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from transformers import AutoTokenizer

def main():
    model_dir = str(root_dir / "results")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    
    print("Default EOS token:", tokenizer.eos_token, "ID:", tokenizer.eos_token_id)
    print("Default PAD token:", tokenizer.pad_token, "ID:", tokenizer.pad_token_id)
    
    # Check if <|im_end|> exists
    im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
    print("Token <|im_end|> ID:", im_end_id)
    
    im_start_id = tokenizer.convert_tokens_to_ids("<|im_start|>")
    print("Token <|im_start|> ID:", im_start_id)

if __name__ == "__main__":
    main()
