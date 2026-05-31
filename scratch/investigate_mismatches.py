import json
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parents[1]
evaluation_file = root_dir / "results" / "evaluation_logic_200.json"
data_file = root_dir / "data" / "logic_based.json"

with open(evaluation_file, "r", encoding="utf-8") as f:
    eval_data = json.load(f)

with open(data_file, "r", encoding="utf-8") as f:
    dataset = json.load(f)

details = eval_data.get("details", [])

# Flat mapping of the dataset to retrieve the correct idx
flat_items = []
for s_idx, sample in enumerate(dataset):
    premises_nl = sample.get("premises-NL", [])
    questions = sample.get("questions", [])
    answers = sample.get("answers", [])
    explanations = sample.get("explanation", [])
    for q_idx, (q, a) in enumerate(zip(questions, answers)):
        flat_items.append({
            "sample_idx": s_idx,
            "question_idx": q_idx,
            "premises_nl": premises_nl,
            "question": q,
            "correct_ans": a,
            "explanation": explanations[q_idx] if q_idx < len(explanations) else "N/A"
        })

print(f"Loaded {len(details)} details and {len(flat_items)} flat items.")

mismatches = [d for d in details if d.get("success") and not d.get("is_match")]

def get_explanation(sample_idx, question_idx):
    for item in flat_items:
        if item["sample_idx"] == sample_idx and item["question_idx"] == question_idx:
            return item["question"], item["explanation"]
    return "N/A", "N/A"

print("\n" + "="*80)
print("INVESTIGATING MISMATCHES")
print("="*80)

for idx, m in enumerate(mismatches):
    s_idx = m["sample_idx"]
    q_idx = m["question_idx"]
    q_text, explanation = get_explanation(s_idx, q_idx)
    
    print(f"\n({idx+1}) S{s_idx}Q{q_idx} | Z3: {m['z3_result']}")
    print(f"  Question     : {q_text}")
    print(f"  Correct Ans  : {m['correct_ans']}")
    print(f"  Predicted Ans: {m['predicted_ans']}")
    print(f"  Explanation  : {explanation}")
    print(f"  ConclusionFOL: {m.get('conclusion_fol', 'N/A')}")
    print(f"  CoT          : {m.get('cot', [])[:2]}")
    
    # Categorize error type
    exp_lower = explanation.lower()
    correct_ans_lower = str(m['correct_ans']).strip().lower()
    predicted_ans_lower = str(m['predicted_ans']).strip().lower()
    
    is_data_error = False
    data_error_reason = ""
    
    if correct_ans_lower in ["yes", "no"]:
        if correct_ans_lower == "no" and ("satisfying all" in exp_lower or "so john can" in exp_lower or "so he meets" in exp_lower or "so professor john can" in exp_lower or "the reasoning is valid and consistent" in exp_lower or "meets all requirements" in exp_lower or "satisfies all conditions" in exp_lower or "entails" in exp_lower or "so she meets" in exp_lower):
            is_data_error = True
            data_error_reason = "Dataset answer is 'No' but explanation says it is logically satisfied (should be 'Yes')"
        elif correct_ans_lower == "yes" and ("insufficient" in exp_lower or "does not meet" in exp_lower or "failing" in exp_lower or "prevent" in exp_lower or "lacks" in exp_lower or "preventing" in exp_lower):
            is_data_error = True
            data_error_reason = "Dataset answer is 'Yes' but explanation says it is NOT logically satisfied (should be 'No')"
            
    # Check for S1Q0 or S2Q0 type MCQ strongest conclusion errors
    if "strongest conclusion" in q_text.lower() and correct_ans_lower != predicted_ans_lower:
        if "making a the strongest conclusion" in exp_lower and correct_ans_lower == "c":
            is_data_error = True
            data_error_reason = "MCQ: Dataset answer is 'C' (weaker) but explanation says 'A' is the strongest conclusion."
            
    if is_data_error:
        print(f"  >>> CATEGORY : [LỖI DATA] {data_error_reason}")
    else:
        print(f"  >>> CATEGORY : [LỖI MODEL] (Translation issue, Z3 Unknown, or Reasoning failure)")
    
    print("-" * 80)
