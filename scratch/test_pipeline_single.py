import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline

def main():
    load_dotenv()
    
    # Setup remote Modal Labs client
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-api.modal.run"
    base_url = f"{modal_url.rstrip('/')}/v1"
    model_name = "exact-qwen3-8b"
    api_key = os.getenv("MODAL_API_KEY") or "modal-placeholder"
    
    print(f"Initializing LLMClient pointing to {base_url}...")
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        use_local=False,
    )
    
    pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)
    
    # S3Q0 Data
    premises_nl = [
        "If a student has completed all required courses, then they are eligible for graduation.",
        "If a student is eligible for graduation and maintains a GPA above 3.5, then they graduate with honors.",
        "If a student graduates with honors and completes a thesis, then they receive academic distinction.",
        "If a student receives academic distinction, then they qualify for the fellowship.",
        "John has completed all required courses.",
        "John maintains a GPA of 3.8.",
        "John completes a thesis."
    ]
    
    question = "Which of the following is correct?\nA. John qualifies for the fellowship.\nB. John needs a faculty recommendation.\nC. John must complete an internship.\nD. John does not graduate with honors."
    
    print("\nRunning pipeline for S3Q0...")
    result = pipeline.run_pipeline(premises_nl, question)
    
    print("\n================ RESULT ================")
    print("Answer predicted:", result["answer"])
    print("Confidence:", result["confidence"])
    print("Conclusion FOL:", result["conclusion_fol"])
    print("Z3 Verification Result:", result["verification"]["result"])
    print("Reasoning steps:")
    for step in result.get("cot", []):
        print(f"  - {step}")

if __name__ == "__main__":
    main()
