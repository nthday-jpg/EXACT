import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline

def main():
    load_dotenv()
    
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-api.modal.run"
    base_url = f"{modal_url.rstrip('/')}/v1"
    model_name = "exact-qwen3-8b"
    api_key = os.getenv("MODAL_API_KEY") or "modal-placeholder"
    
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        use_local=False,
    )
    
    pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)
    
    premises_nl = [
        "If a faculty member has completed training, they can teach undergraduate courses.",
        "If a faculty member can teach undergraduate courses and holds a PhD, they can supervise graduate students.",
        "If a faculty member can supervise graduate students and has at least 3 publications, they can serve on curriculum committees.",
        "If a faculty member can serve on curriculum committees and has a positive teaching evaluation, they can propose new courses.",
        "Professor John has completed pedagogical training.",
        "Professor John holds a PhD.",
        "Professor John has published at least 3 academic papers.",
        "Professor John has received a positive teaching evaluation."
    ]
    
    options = [
        "He can teach undergraduate courses but cannot supervise graduates",
        "He can serve on curriculum committees but cannot propose courses",
        "He can propose new courses",
        "He needs more publications to serve on committees"
    ]
    
    combined_nl = premises_nl + options
    all_fol = pipeline.translation_pipeline.translate_list(combined_nl)
    
    print("\nPremises FOL:")
    for idx, p in enumerate(all_fol[:len(premises_nl)]):
        print(f"  P{idx+1}: {premises_nl[idx]} -> {p}")
        
    print("\nOptions FOL:")
    for idx, opt in enumerate(all_fol[len(premises_nl):]):
        print(f"  Opt {chr(65+idx)}: {options[idx]} -> {opt}")

if __name__ == "__main__":
    main()
