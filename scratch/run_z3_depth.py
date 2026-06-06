import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Add project root directory to sys.path
root_dir = Path(r"d:\mduy\source\repos\EXACT")
sys.path.append(str(root_dir))

from src.logic.reasoning.verifier import verify_with_z3

file_path = root_dir / "data" / "processed" / "logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Loaded {len(data)} samples.")

# Test Z3 verification on first 50 samples to verify feasibility and speed
import time
start_time = time.time()
depths = []
success_count = 0

for i, d in enumerate(data[:100]):
    prems = d.get("premises-FOL", [])
    # Reconstruct question as conclusion
    # For statements (True/False/Unknown or Yes/No/Unknown):
    # If the answer is True/Yes, we check if the question is entailed
    # If the answer is False/No, we check if NOT question is entailed
    # If Unknown, we skip unsat core check (depth is not applicable / 0)
    ans = d.get("answer", "")
    q = d.get("question", "")
    
    # Simple check for MCQs: conclusion is not easily represented as a single statement from the question field 
    # without translation. So for this test, we can just check if we can verify statements.
    if ans in ["True", "Yes", "False", "No"]:
        # We need conclusion FOL, which is not directly stored in the file if it hasn't been translated.
        # Wait, does the original dataset have conclusion FOL?
        # Let's check the sample keys again. No, there is no conclusion FOL, only premises-FOL.
        # Wait! If the original dataset doesn't have conclusion FOL, how can we run Z3?
        # Ah! We cannot run verify_with_z3 easily without translating the conclusion/question into FOL!
        pass

print("Done checking. Conclusion FOL is not present, so we can't run Z3 verify directly without translation.")
