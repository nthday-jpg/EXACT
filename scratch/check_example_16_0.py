import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    if item.get("example_id") == "16_0":
        print(json.dumps(item, indent=2, ensure_ascii=False))
        break
