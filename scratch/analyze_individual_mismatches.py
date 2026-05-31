import json
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parents[1]
data_path = root_dir / "data" / "logic_based.json"

with open(data_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)

# List of mismatched (sample_idx, question_idx, z3_result) from the log
mismatches_log = [
    (2, 1, "unknown"),
    (0, 1, "unknown"),
    (1, 1, "unknown"),
    (0, 0, "unknown"),
    (6, 0, "sat"),
    (6, 1, "sat"),
    (5, 1, "sat"),
    (8, 0, "unsat"),
    (7, 1, "sat"),
    (9, 1, "sat"),
    (8, 1, "sat"),
    (11, 0, "sat"),
    (12, 1, "unknown"),
    (12, 0, "unknown"),
    (13, 1, "unsat"),
    (15, 1, "sat"),
    (1, 0, "unknown"),
    (14, 1, "unknown"),
    (2, 0, "unknown"),
    (16, 1, "sat"),
    (17, 1, "unsat"),
    (21, 1, "sat"),
    (11, 1, "sat"),
    (22, 1, "unknown"),
    (20, 1, "unknown"),
    (17, 0, "unsat"),
    (23, 1, "sat")
]

print("=" * 80)
print(f"ANALYZING {len(mismatches_log)} MISMATCHED SAMPLES FROM LOG")
print("=" * 80)

for idx, (s_idx, q_idx, z3_res) in enumerate(mismatches_log):
    sample = dataset[s_idx]
    premises_nl = sample.get("premises-NL", [])
    question = sample.get("questions", [])[q_idx]
    ans = sample.get("answers", [])[q_idx]
    explanation = sample.get("explanation", [])[q_idx]
    
    print(f"\n({idx+1}) S{s_idx}Q{q_idx} | Z3 Result in Log: {z3_res}")
    print(f"  Question NL: {question}")
    print(f"  GT Answer  : {ans}")
    print(f"  Explanation: {explanation}")
    
    # Categorize
    exp_lower = explanation.lower()
    ans_clean = str(ans).strip().lower()
    
    is_data_error = False
    reason = ""
    
    if ans_clean in ["yes", "no"]:
        if ans_clean == "no" and ("satisfying all" in exp_lower or "so john can" in exp_lower or "so he meets" in exp_lower or "so professor john can" in exp_lower or "the reasoning is valid and consistent" in exp_lower or "meets all requirements" in exp_lower or "satisfies all conditions" in exp_lower or "entails" in exp_lower or "so she meets" in exp_lower or "satisfies the requirements" in exp_lower or "so minh qualifies" in exp_lower):
            is_data_error = True
            reason = "Dataset Answer is 'No' but Explanation explicitly states it is logically satisfied (should be 'Yes')."
        elif ans_clean == "yes" and ("insufficient" in exp_lower or "does not meet" in exp_lower or "fail to" in exp_lower or "prevent" in exp_lower or "lacks" in exp_lower or "preventing" in exp_lower or "fails the" in exp_lower):
            is_data_error = True
            reason = "Dataset Answer is 'Yes' but Explanation explicitly states it is NOT logically satisfied (should be 'No')."
            
    if "strongest conclusion" in question.lower():
        if "making a the strongest conclusion" in exp_lower and ans_clean == "c":
            is_data_error = True
            reason = "MCQ: Dataset Answer is C (weaker option) but Explanation says A is the strongest conclusion."
        elif "making a the strongest conclusion" in exp_lower and ans_clean == "b":
            is_data_error = True
            reason = "MCQ: Dataset Answer is B but Explanation says A is the strongest conclusion."
            
    if is_data_error:
        print(f"  >>> CATEGORY : [LỖI DATA] {reason}")
    else:
        # Check Z3 result context
        if z3_res == "unknown":
            print(f"  >>> CATEGORY : [LỖI MODEL / PIPELINE] (Z3 returned unknown, likely due to model translation loops/truncation on Modal)")
        elif z3_res == "sat":
            print(f"  >>> CATEGORY : [LỖI MODEL] (Model translated predicates or implications incorrectly, or Z3 found a valid counterexample)")
        elif z3_res == "unsat":
            print(f"  >>> CATEGORY : [LỖI MODEL/PIPELINE] (Z3 proved it, but the pipeline returned a different answer, or translation was inconsistent)")
            
    print("-" * 80)
