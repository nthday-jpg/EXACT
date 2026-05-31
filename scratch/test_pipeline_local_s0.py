import sys
import os
import torch
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))
load_dotenv()

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline

def main():
    client = LLMClient(
        model_name="Qwen/Qwen3-8B",
        use_local=True,
        model_dir=str(root_dir / "results")
    )
    
    print("Loading local fine-tuned model...")
    client.load_local_model()
    
    pipeline = LogicalReasoningPipeline(use_local=True, llm_client=client)
    
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
        "If a Python project is not well-structured, then it does not follow PEP 8 standards.",
    ]
    
    conclusion_nl = "Does it follow that if all Python projects are well-structured, then all Python projects are optimized, according to the premises?"
    
    print("\n--- Running Translate List on Premises + Conclusion ---")
    p_fol, c_fol = pipeline.translate_premises_and_conclusion(premises_nl, conclusion_nl)
    
    print("\nTranslated Premises FOL:")
    for idx, fol in enumerate(p_fol):
        print(f"  {idx+1:2d}. {premises_nl[idx]} -> {fol}")
        
    print(f"\nConclusion NL: {conclusion_nl}")
    print(f"Translated Conclusion FOL: {c_fol}")
    
    # Run the full pipeline for S0Q1
    print("\n--- Running Full Pipeline on S0Q1 ---")
    res = pipeline.run_pipeline(premises_nl, conclusion_nl)
    print("Answer:", res["answer"])
    print("Confidence:", res["confidence"])
    print("Verification Result:", res["verification"]["result"])

if __name__ == "__main__":
    main()
