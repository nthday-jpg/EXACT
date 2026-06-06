import os
import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(r"d:\mduy\source\repos\EXACT")
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient

# Initialize client using Hugging Face router
try:
    client = LLMClient(
        model_name="Qwen/Qwen3-8B:featherless-ai",
        base_url="https://router.huggingface.co/v1",
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
