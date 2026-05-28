import json
import z3
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
evaluation_file = root_dir / "results" / "evaluation_logic_200.json"

with open(evaluation_file, "r", encoding="utf-8") as f:
    data = json.load(f)

details = data["details"]
print(f"Loaded {len(details)} evaluation details.")

# Find details where Z3 is unsat but it was a MISMATCH
mismatches_unsat = [d for d in details if not d.get("is_match") and d.get("z3_result") == "unsat"]
print(f"Found {len(mismatches_unsat)} mismatches where Z3 returned unsat.")

# Let's inspect the first 5 mismatches
from src.logic.reasoning.verifier import parse_formulas

for idx, d in enumerate(mismatches_unsat[:5]):
    eval_idx = d["eval_idx"]
    correct = d["correct_ans"]
    predicted = d["predicted_ans"]
    
    # Let's load the corresponding sample from logic_based.json
    with open(root_dir / "data" / "logic_based.json", "r", encoding="utf-8") as f:
        logic_data = json.load(f)
    
    # Flat dataset mapping
    items = []
    for s_idx, sample in enumerate(logic_data):
        premises_nl = sample.get("premises-NL", [])
        questions = sample.get("questions", [])
        answers = sample.get("answers", [])
        for q_idx, (q, a) in enumerate(zip(questions, answers)):
            items.append({
                "premises_nl": premises_nl,
                "question": q,
                "correct_ans": a,
                "sample_idx": s_idx
            })
    
    item = items[eval_idx]
    premises_nl = item["premises_nl"]
    
    print(f"\n==================================================")
    print(f"Mismatch #{idx+1} (Eval Index {eval_idx}):")
    print(f"Correct: {correct} | Predicted: {predicted}")
    
    # We want to translate the premises of this sample and check their consistency in Z3!
    # Wait, we can see if the evaluation json saved the translated formulas!
    # Ah, the evaluation json does not save the premises_fol in the detail dictionary.
    # Let's run a quick translation on these premises and check consistency!
    
