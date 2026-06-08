import json
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas
from src.logic.pipeline import ReasoningPipeline

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

qa_incorrect_cases = [item for item in failed_cases if not item.get("is_qa_correct")]

print(f"Analyzing {len(qa_incorrect_cases)} QA incorrect cases using GT FOL...")

logically_incorrect_gt_labels = 0
correct_gt_labels = 0

for item in qa_incorrect_cases:
    example_id = item.get("example_id")
    gt_premises = item.get("premises-FOL-GT", [])
    question = item.get("question", "")
    gt_answer = item.get("answer-GT", "")
    
    if not gt_premises or not question or not gt_answer:
        continue
        
    # Let's check if GT premises are consistent first
    try:
        symbols, exprs = parse_formulas(gt_premises)
    except Exception:
        continue
        
    solver = z3.Solver()
    for e in exprs:
        solver.add(e)
    if solver.check() == z3.unsat:
        # Contradictory premises
        print(f"Case {example_id}: GT Premises are contradictory!")
        logically_incorrect_gt_labels += 1
        continue
        
    # Verify the GT answer using GT premises
    # Let's see if the GT answer is logically supported
    # If the GT answer is "Yes" / "True", the conclusion must be entailed.
    # If "No" / "False", the negated conclusion must be entailed.
    # If "Unknown", neither must be entailed.
    
    # We need to translate the question/conclusion to FOL.
    # But wait, we don't have the GT FOL for the question/conclusion in the failed cases json!
    # Wait, does the failed cases json have the GT question/conclusion FOL?
    # No, it only has premises-FOL-GT.
    # But wait, if it's a multiple choice question, one of the choices (the GT one) should be entailed.
    # Wait, since we don't have the GT option FOL, we can't easily verify the options automatically.
    # But for True/False questions (where answer-GT is True/False/Unknown), we can check if the question itself is in the dataset.
    # Let's see.
    pass
