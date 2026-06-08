import json

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

qa_incorrect_cases = [item for item in failed_cases if not item.get("is_qa_correct")]
qa_correct_cases = [item for item in failed_cases if item.get("is_qa_correct")]

print(f"Total entries in fol_failed_cases.json: {len(failed_cases)}")
print(f"Entries where is_qa_correct is False: {len(qa_incorrect_cases)}")
print(f"Entries where is_qa_correct is True (but EM is False): {len(qa_correct_cases)}")
