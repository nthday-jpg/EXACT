import json

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

qa_incorrect_cases = [item for item in failed_cases if not item.get("is_qa_correct")]

with open(r"d:\mduy\source\repos\EXACT\scratch\qa_failures.txt", "w", encoding="utf-8") as f_out:
    f_out.write(f"=== {len(qa_incorrect_cases)} QA INCORRECT CASES ===\n")
    for idx, item in enumerate(qa_incorrect_cases):
        f_out.write(f"\n=================== Failed Case {idx+1} (ID: {item.get('example_id')}) ===================\n")
        f_out.write("NL Premises:\n")
        for p in item.get("premises-NL", []):
            f_out.write(f"  - {p}\n")
        f_out.write("GT FOL:\n")
        for p in item.get("premises-FOL-GT", []):
            f_out.write(f"  - {p}\n")
        f_out.write("Pred FOL:\n")
        for p in item.get("premises-FOL-Pred", []):
            f_out.write(f"  - {p}\n")
        f_out.write(f"Question: {item.get('question')}\n")
        f_out.write(f"GT Answer: {item.get('answer-GT')}\n")
        f_out.write(f"Pred Answer: {item.get('answer-Pred')}\n")
        f_out.write(f"is_syntax_valid: {item.get('is_syntax_valid')}\n")
