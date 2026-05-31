import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Enable Z3 proof generation globally before importing other Z3 modules
import z3
z3.set_param('proof', True)
from z3 import unsat, sat

from src.logic import LogicalReasoningPipeline

# Preset samples for testing contradiction
SAMPLES = {
    0: {
        "name": "Python Project Optimization",
        "conclusion": "If all Python projects are well-structured, then all Python projects are optimized."
    },
    1: {
        "name": "Sophia's Scholarship",
        "conclusion": "Sophia qualifies for the university scholarship."
    },
    3: {
        "name": "John's Fellowship",
        "conclusion": "John qualifies for the graduate fellowship program."
    },
    13: {
        "name": "Sarah's Course Eligibility",
        "conclusion": "Sarah is eligible for advanced classes."
    }
}

def main():
    load_dotenv()
    
    # 1. Load unprocessed dataset
    data_path = root_dir / "data" / "logic_based.json"
    if not data_path.exists():
        print(f"ERROR: Dataset not found at {data_path}")
        sys.exit(1)
        
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    # Select sample (Default is Sophia's Scholarship - index 1)
    sample_idx = 1
    sample_info = SAMPLES[sample_idx]
    sample = dataset[sample_idx]
    
    premises_nl = sample["premises-NL"]
    conclusion_nl = sample_info["conclusion"]
    
    print(f"\n[Step 4] Selected Sample: {sample_info['name']} (Index {sample_idx})")
    print("\n--- Unprocessed Natural Language Premises ---")
    for i, premise in enumerate(premises_nl, 1):
        print(f"{i}. {premise}")
    print(f"\n--- Intended Conclusion (True Statement) ---")
    print(f"C. {conclusion_nl}")
    print("-" * 70)
    
    # Force use_local=True to run and test the local model directly as requested
    print("\n[Step 5] Running pipeline locally via GPU model...")
    pipeline = LogicalReasoningPipeline(use_local=True)
    results = pipeline.run_pipeline(premises_nl, conclusion_nl)
    
    # Print results
    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    
    verification = results["verification"]
    res = verification["result"]
    
    if res == unsat:
        print("\nSUCCESS: Contradiction proven! The conclusion is logically guaranteed.")
        print("\nUnsat Core (Contributing Premises):", [str(p) for p in verification["unsat_core"] if str(p).startswith("p_")])
        print("\n--- Formal Z3 Contradiction Proof ---")
        print(verification["proof"])
    elif res == sat:
        print("\nWARNING: Consistent set of formulas. Conclusion is NOT logically guaranteed.")
        print("\n--- Z3 Counterexample Model ---")
        print(verification["model"])
    else:
        print("\nZ3 could not determine satisfiability (UNKNOWN).")
        
    print("\n--- Generated Natural Language Reasoning Explanation ---")
    print(results["reasoning"])
    print("=" * 70)

if __name__ == "__main__":
    main()
