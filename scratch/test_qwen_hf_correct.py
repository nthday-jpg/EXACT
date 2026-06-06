import os
import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(r"d:\mduy\source\repos\EXACT")
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient

try:
    # Use standard Qwen2.5-7B-Instruct from the HF Hub
    client = LLMClient(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ.get("HF_API_KEY"),
        temperature=0.0
    )
    print("Client initialized successfully.")
    
    response = client.generate(
        prompt="Convert this sentence to FOL: Socrates is a human.",
        system_prompt="You are a logic translator."
    )
    print("Response:")
    print(response["content"])
except Exception as e:
    print(f"Error occurred: {e}")
