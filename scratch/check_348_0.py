import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

for item in failed_cases:
    if item.get("example_id") == "348_0":
        print(json.dumps(item, indent=2, ensure_ascii=False))
        break
