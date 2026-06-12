import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

data_dir = Path(r"d:\mduy\source\repos\EXACT\data")
for p in data_dir.glob("**/*.json"):
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if item.get("example_id") == "16_0":
                        print(f"Found 16_0 in {p.name} at index {idx}")
            elif isinstance(data, dict):
                # check if example_id is key or in values
                if "16_0" in data:
                    print(f"Found 16_0 as key in {p.name}")
    except Exception as e:
        print(f"Error reading {p.name}: {e}")
