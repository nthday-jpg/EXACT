import json
import re
import sys
from pathlib import Path

# Set up encoding for Windows console
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.logic.reasoning.parser import try_parse_fol

file_path = Path("d:/mduy/source/repos/EXACT/data/fol_failed_cases.json")
if not file_path.exists():
    print(f"Error: {file_path} does not exist.")
    sys.exit(1)

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total failed cases: {len(data)}")

# Filter cases where is_qa_correct is False
qa_incorrect_cases = [c for c in data if c.get("is_qa_correct") == False]
print(f"Failed cases with is_qa_correct = False: {len(qa_incorrect_cases)}")

# Analyze types of mismatches in QA-incorrect cases
exact_match_f = 0
syntax_invalid_f = 0
both_f = 0

for c in qa_incorrect_cases:
    em = c.get("is_exact_match")
    sv = c.get("is_syntax_valid")
    if not em and not sv:
        both_f += 1
    elif not em:
        exact_match_f += 1
    elif not sv:
        syntax_invalid_f += 1

print(f"  - Failed Exact Match only: {exact_match_f}")
print(f"  - Failed Syntax Validity only: {syntax_invalid_f}")
print(f"  - Failed both: {both_f}")

print("\n--- SAMPLE 1: Exact Match Failure & QA Incorrect ---")
em_samples = [c for c in qa_incorrect_cases if not c.get("is_exact_match") and c.get("is_syntax_valid")][:4]
for idx, c in enumerate(em_samples):
    print(f"\n({idx+1}) Example ID: {c['example_id']}")
    print(f"  Question: {c['question']}")
    print(f"  GT Answer  : {c['answer-GT']}")
    print(f"  Pred Answer: {c['answer-Pred']}")
    print(f"  NL Premises:")
    for nl in c['premises-NL'][:3]:
        print(f"    - {nl}")
    if len(c['premises-NL']) > 3:
        print(f"    - ...")
    print(f"  GT FOL:")
    for gt in c['premises-FOL-GT'][:3]:
        print(f"    - {gt}")
    if len(c['premises-FOL-GT']) > 3:
        print(f"    - ...")
    print(f"  Pred FOL:")
    for pred in c['premises-FOL-Pred'][:3]:
        print(f"    - {pred}")
    if len(c['premises-FOL-Pred']) > 3:
        print(f"    - ...")
        
    # Compare first mismatching formulas
    print(f"  Mismatches between GT and Pred:")
    for f_idx, (gt, pred) in enumerate(zip(c['premises-FOL-GT'], c['premises-FOL-Pred'])):
        if gt.strip() != pred.strip():
            print(f"    [{f_idx+1}] GT  : {gt}")
            print(f"    [{f_idx+1}] Pred: {pred}")
            break

print("\n--- SAMPLE 2: Syntax Validity Failure & QA Incorrect ---")
sv_samples = [c for c in qa_incorrect_cases if not c.get("is_syntax_valid")][:4]
for idx, c in enumerate(sv_samples):
    print(f"\n({idx+1}) Example ID: {c['example_id']}")
    print(f"  Question: {c['question']}")
    print(f"  GT Answer  : {c['answer-GT']}")
    print(f"  Pred Answer: {c['answer-Pred']}")
    print(f"  Pred FOL:")
    for pred in c['premises-FOL-Pred']:
        print(f"    - {pred}")
    print(f"  Why failed syntax validity?")
    for f_idx, formula in enumerate(c['premises-FOL-Pred']):
        ok, err = try_parse_fol(formula)
        if not ok:
            print(f"    Formula {f_idx+1}: {formula} -> Error: {err}")
