import json

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

qa_incorrect_cases = [item for item in failed_cases if not item.get("is_qa_correct")]

unknown_gt_count = sum(1 for item in qa_incorrect_cases if item.get("answer-GT") == "Unknown")

print(f"Total QA incorrect cases: {len(qa_incorrect_cases)}")
print(f"Cases where GT Answer is 'Unknown': {unknown_gt_count} ({unknown_gt_count/len(qa_incorrect_cases)*100:.2f}%)")
