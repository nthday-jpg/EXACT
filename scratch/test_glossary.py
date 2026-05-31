import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

load_dotenv()

from src.llm.llm_client import LLMClient
from src.logic.translation.pipeline import NLToFOLPipeline

def main():
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run"
    base_url = f"{modal_url}/v1"
    model_name = "exact-qwen3-8b"
    api_key = "modal-placeholder"

    print("Initializing LLMClient...")
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        use_local=False,
    )
    
    pipeline = NLToFOLPipeline(use_local=False, llm_client=client)

    # Sample premises from logic_based.json
    premises_nl = [
      "If a Python code is well-tested, then the project is optimized.",
      "If a Python code does not follow PEP 8 standards, then it is not well-tested.",
      "All Python projects are easy to maintain.",
      "All Python code is well-tested.",
      "If a Python code follows PEP 8 standards, then it is easy to maintain.",
      "If a Python code is well-tested, then it follows PEP 8 standards.",
      "If a Python project is well-structured, then it is optimized.",
      "If a Python project is easy to maintain, then it is well-tested.",
      "If a Python project is optimized, then it has clean and readable code.",
      "All Python projects are well-structured.",
      "All Python projects have clean and readable code.",
      "There exists at least one Python project that follows best practices.",
      "There exists at least one Python project that is optimized.",
      "If a Python project is not well-structured, then it does not follow PEP 8 standards."
    ]

    print("\n--- Running Glossary Generation ---")
    glossary = pipeline.generate_glossary(premises_nl)
    print("Glossary output:")
    print(json.dumps(glossary, indent=2))

    if glossary:
        print("\n--- Running Glossary-Constrained Translation ---")
        # Enforce is_finetuned = False for this call to test two-stage
        from unittest.mock import patch
        with patch.object(pipeline.llm_client, "model_name", "some-other-model"):
            formulas = pipeline.translate_list(premises_nl)
            print("Formulas:")
            for i, f in enumerate(formulas, 1):
                print(f"{i}. {f}")

if __name__ == "__main__":
    main()
