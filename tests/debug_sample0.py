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
        temperature=0.3,
        frequency_penalty=1.0,
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

    question = "Which conclusion follows with the fewest premises?\nA. If a Python project is not optimized, then it is not well-tested\nB. If all Python projects are optimized, then all Python projects are well-structured\nC. If a Python project is well-tested, then it must be clean and readable\nD. If a Python project is not optimized, then it does not follow PEP 8 standards"

    print("Running pipeline for Sample 0 Question 0...")
    res = pipeline.run_pipeline(premises, question)
    print("\n--- Pipeline Result ---")
    print(f"Predicted Answer: {res['answer']}")
    print(f"Confidence: {res['confidence']}")
    print(f"Conclusion FOL: {res['conclusion_fol']}")
    if 'verification' in res:
        print(f"Z3 Result: {res['verification'].get('result')}")
        print(f"Unsat Core: {res['verification'].get('unsat_core')}")
    print(f"Reasoning:\n{res['reasoning']}")

if __name__ == "__main__":
    main()
