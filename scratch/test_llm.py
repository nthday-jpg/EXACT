import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm import LLMClient

try:
    print("Initializing LLMClient...")
    llm_client = LLMClient(
        model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
        temperature=0.1
    )
    llm_client.tokenizer = None  # Force chat completions

    
    print("Testing generate_text...")
    response = llm_client.generate_text("Say hello in one word.")
    print("Response:", response)
except Exception as e:
    print("Failed:", e)
