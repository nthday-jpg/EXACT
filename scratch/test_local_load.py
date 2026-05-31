import sys
import torch
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient

def main():
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Device name:", torch.cuda.get_device_name(0))
        
    client = LLMClient(
        model_name="Qwen/Qwen3-8B",
        use_local=True,
        model_dir=str(root_dir / "results")
    )
    
    print("Loading local model (this may take a minute)...")
    client.load_local_model()
    print("Model loaded successfully!")
    
    prompt = "Translate the following natural language sentence to First-Order Logic (FOL):\nSentence: John is a student."
    print(f"\nGenerating for test prompt:\n{prompt}")
    res = client.generate_text(prompt, max_new_tokens=64)
    print("\nGenerated Response:")
    print(res)

if __name__ == "__main__":
    main()
