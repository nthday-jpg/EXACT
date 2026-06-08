import json
import sys

# Configure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)


qa_incorrect_cases = [item for item in failed_cases if not item.get("is_qa_correct")]
non_unknown_failures = [item for item in qa_incorrect_cases if item.get("answer-GT") != "Unknown"]

print(f"Total non-Unknown incorrect cases: {len(non_unknown_failures)}")

for idx, item in enumerate(non_unknown_failures[:10]):
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
