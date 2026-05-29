import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
data_path = root_dir / "data" / "logic_based.json"

with open(data_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)

corrupted_count = 0
total_yes_no = 0

print("=" * 80)
print("SCANNING THE ENTIRE DATASET FOR INCORRECT LABELS")
print("=" * 80)

for idx, sample in enumerate(dataset):
    questions = sample.get("questions", [])
    answers = sample.get("answers", [])
    explanations = sample.get("explanation", [])
    
    # Check each question
    for q_idx, (q_nl, ans) in enumerate(zip(questions, answers)):
        exp = explanations[q_idx] if q_idx < len(explanations) else ""
        ans_clean = str(ans).strip().lower()
        
        # We only care about Yes/No questions
        if ans_clean in ["yes", "no"]:
            total_yes_no += 1
            exp_lower = exp.lower()
            
            # Logic check:
            # If answer is 'no' but explanation has words indicating it succeeds:
            is_corrupted = False
            reason = ""
            
            if ans_clean == "no":
                pos_phrases = [
                    "satisfying all conditions", 
                    "satisfies all", 
                    "so john can", 
                    "so professor john can",
                    "so dr. john can",
                    "so he meets", 
                    "so she meets",
                    "so alex meets",
                    "entails", 
                    "the reasoning is valid and consistent", 
                    "supports the statement", 
                    "is logically valid",
                    "satisfying the requirement",
                    "can supervise",
                    "can teach",
                    "meets all requirements",
                    "does meet the requirement",
                    "is eligible"
                ]
                for phrase in pos_phrases:
                    if phrase in exp_lower:
                        is_corrupted = True
                        reason = f"Answer is 'No' but explanation says '{phrase}'"
                        break
            
            elif ans_clean == "yes":
                neg_phrases = [
                    "insufficient", 
                    "does not meet", 
                    "fail to", 
                    "failing", 
                    "lacks", 
                    "preventing", 
                    "prevents",
                    "cannot teach",
                    "cannot supervise",
                    "is not qualified"
                ]
                for phrase in neg_phrases:
                    if phrase in exp_lower:
                        is_corrupted = True
                        reason = f"Answer is 'Yes' but explanation says '{phrase}'"
                        break
                        
            if is_corrupted:
                corrupted_count += 1
                print(f"Sample {idx:3d} | Q {q_idx} | GT Answer: {ans:3s} | Mismatch Reason: {reason}")

print("-" * 80)
print(f"Total Yes/No questions scanned: {total_yes_no}")
print(f"Detected corrupted/contradictory labels: {corrupted_count} ({corrupted_count/total_yes_no*100:.2f}%)")
print("=" * 80)
