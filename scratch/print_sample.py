import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
data_path = root_dir / "data" / "logic_based.json"

with open(data_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)

for idx in [4, 5, 6, 7]:
    sample = dataset[idx]
    print(f"\n========================================")
    print(f"Sample {idx}:")
    print(f"Premises-NL:")
    for p in sample.get("premises-NL", []):
        print(f"  - {p}")
    print(f"Questions:")
    for q in sample.get("questions", []):
        print(f"  - {q}")
    print(f"Answers:")
    for a in sample.get("answers", []):
        print(f"  - {a}")
