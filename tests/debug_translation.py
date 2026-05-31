import os
import sys
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

load_dotenv()

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline

def main():
    client = LLMClient(
        model_name="exact-qwen3-8b",
        api_key="modal-placeholder",
        base_url="https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run/v1",
        temperature=0.1,
        extra_body={},
        use_local=False,
    )
    pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)

    premises = [
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

    options = {
        "A": "If a Python project is not optimized, then it is not well-tested",
        "B": "If all Python projects are optimized, then all Python projects are well-structured",
        "C": "If a Python project is well-tested, then it must be clean and readable",
        "D": "If a Python project is not optimized, then it does not follow PEP 8 standards"
    }

    print("Translating premises...")
    premises_fol = pipeline.translation_pipeline.translate_list(premises)
    print("\n--- Premises FOL ---")
    for i, fol in enumerate(premises_fol, 1):
        print(f"P{i}: {fol}")

    print("\nTranslating options...")
    options_fol = {}
    for k, v in options.items():
        fol_list = pipeline.translation_pipeline.translate_list([v])
        options_fol[k] = fol_list[0] if fol_list else ""
        print(f"Opt {k}: {options_fol[k]}")

if __name__ == "__main__":
    main()
