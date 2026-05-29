import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))
load_dotenv()

from src.llm.llm_client import LLMClient

def main():
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run"
    base_url = f"{modal_url.rstrip('/')}/v1"
    model_name = "exact-qwen3-8b"
    api_key = os.getenv("MODAL_API_KEY") or "modal-placeholder"
    
    print("Initializing LLMClient...")
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.0,
        use_local=False,
    )
    
    print("====================================")
    print("Tokenizer loaded:", client.tokenizer is not None)
    if client.tokenizer:
        print("Tokenizer class:", client.tokenizer.__class__.__name__)
        print("Model dir:", client.model_dir)
        
        # Test chat template rendering
        messages = [
            {"role": "system", "content": "You are a logic translator."},
            {"role": "user", "content": "If it rains, the grass is wet."}
        ]
        chat_prompt = client.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        print("\nRendered prompt:")
        print(chat_prompt)
    print("====================================")

if __name__ == "__main__":
    main()
