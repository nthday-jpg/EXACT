import os
import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(r"d:\mduy\source\repos\EXACT")
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient

try:
    client = LLMClient(
        model_name="exact-qwen3-8b",
        base_url="https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run/v1",
        api_key="modal-placeholder",
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
