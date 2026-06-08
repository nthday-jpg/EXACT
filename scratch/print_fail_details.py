import json
import sys
from pathlib import Path

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

for idx, item in enumerate(failed_cases[:10]):
    print(f"\n=================== Failed Case {idx+1} (ID: {item.get('example_id')}) ===================")
    print("NL Premises:")
    for p in item.get("premises-NL", []):
        print("  -", p)
    print("GT FOL:")
    for p in item.get("premises-FOL-GT", []):
        print("  -", p)
    print("Pred FOL:")
    for p in item.get("premises-FOL-Pred", []):
        print("  -", p)
    print("Question:", item.get("question"))
    print("GT Answer:", item.get("answer-GT"))
    print("Pred Answer:", item.get("answer-Pred"))
    print("is_qa_correct:", item.get("is_qa_correct"))
