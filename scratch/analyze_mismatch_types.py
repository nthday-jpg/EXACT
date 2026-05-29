import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
evaluation_file = root_dir / "results" / "evaluation_logic_200.json"

with open(evaluation_file, "r", encoding="utf-8") as f:
    data = json.load(f)

details = data.get("details", [])
mismatches = [d for d in details if d.get("success") and not d.get("is_match")]

print("=" * 80)
print(f"ANALYZING {len(mismatches)} MISMATCHES IN DETAILS")
print("=" * 80)

for idx, m in enumerate(mismatches):
    print(f"\n({idx+1}) Eval {m['eval_idx']} | Sample {m['sample_idx']} Question {m['question_idx']}")
    print(f"  Question NL: {m.get('question_nl', 'N/A')}")
    print(f"  Correct Ans: {m['correct_ans']} | Predicted: {m['predicted_ans']}")
    print(f"  Z3 Result  : {m['z3_result']}")
    print(f"  Conclusion FOL: {m.get('conclusion_fol', 'N/A')}")
    
    # Load dataset sample to see the explanation and premises
    with open(root_dir / "data" / "logic_based.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
    sample = dataset[m['sample_idx']]
    print(f"  Premises NL:")
    for p in sample.get("premises-NL", [])[:3]:
        print(f"    - {p}")
    if len(sample.get("premises-NL", [])) > 3:
        print(f"    - ... ({len(sample.get('premises-NL', [])) - 3} more)")
    print(f"  Dataset Q: {sample.get('questions', [])[m['question_idx']]}")
    print(f"  Dataset Explanation: {sample.get('explanation', [])[m['question_idx']] if m['question_idx'] < len(sample.get('explanation', [])) else 'N/A'}")
    print(f"  CoT Steps:")
    for step in m.get("cot", [])[:3]:
        print(f"    - {step}")
    if len(m.get("cot", [])) > 3:
        print(f"    - ... ({len(m.get('cot', [])) - 3} more)")
    print("-" * 80)
