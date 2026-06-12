import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\logic_based.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total items in logic_based.json: {len(data)}")
for item in data[:3]:
    print(json.dumps(item, indent=2, ensure_ascii=False))
    print("-" * 50)
