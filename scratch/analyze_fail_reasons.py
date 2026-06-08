import json
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

print(f"Total failed cases: {len(failed_cases)}")

inconsistent_premises_count = 0
open_world_implication_count = 0
syntax_invalid_count = 0
other_count = 0

for item in failed_cases:
    example_id = item.get("example_id")
    pred_premises = item.get("premises-FOL-Pred", [])
    
    if not pred_premises:
        continue
        
    # Check syntax validity
    try:
        symbols, exprs = parse_formulas(pred_premises)
    except Exception as e:
        syntax_invalid_count += 1
        continue
        
    # Check premise consistency
    solver = z3.Solver()
    for expr in exprs:
        solver.add(expr)
    if solver.check() == z3.unsat:
        inconsistent_premises_count += 1
        print(f"Case {example_id} has inconsistent premises!")
        continue
        
    other_count += 1

print("\n--- Failure Analysis Summary ---")
print(f"Syntax invalid: {syntax_invalid_count}")
print(f"Inconsistent premises (contradictions): {inconsistent_premises_count}")
print(f"Other logic/translation mismatches: {other_count}")
