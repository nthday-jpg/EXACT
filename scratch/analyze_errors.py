import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
evaluation_file = root_dir / "results" / "evaluation_logic_200.json"

if not evaluation_file.exists():
    print(f"Error: {evaluation_file} does not exist.")
    exit(1)

with open(evaluation_file, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data.get("evaluation_summary", {})
details = data.get("details", [])

print("=" * 60)
print("EVALUATION RUN SUMMARY")
print("=" * 60)
for k, v in summary.items():
    if k != "z3_stats":
        print(f"{k}: {v}")
print("Z3 stats:")
for k, v in summary.get("z3_stats", {}).items():
    print(f"  {k}: {v}")
print("=" * 60)

mismatches = [d for d in details if d.get("success") and not d.get("is_match")]
print(f"Total mismatches: {len(mismatches)}")

# Categorize mismatches by z3_result
mismatches_by_z3 = {}
for m in mismatches:
    z3_res = m.get("z3_result", "unknown")
    mismatches_by_z3.setdefault(z3_res, []).append(m)

for z3_res, items in mismatches_by_z3.items():
    print(f"Z3 result '{z3_res}': {len(items)} mismatches")

print("\n--- SAMPLE MISMATCHES ---")
for idx, m in enumerate(mismatches[:15]):
    print(f"\n({idx+1}) Eval {m['eval_idx']} (S{m['sample_idx']}Q{m['question_idx']}):")
    print(f"  Correct Ans  : {m['correct_ans']}")
    print(f"  Predicted Ans: {m['predicted_ans']}")
    print(f"  Z3 Result    : {m['z3_result']}")
    print(f"  FOL          : {m.get('conclusion_fol', '')}")
    if m.get("cot"):
        print(f"  CoT (first 2 steps): {m['cot'][:2]}")
