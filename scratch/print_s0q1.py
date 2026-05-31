import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
evaluation_file = root_dir / "results" / "evaluation_logic_200.json"

with open(evaluation_file, "r", encoding="utf-8") as f:
    data = json.load(f)

details = data.get("details", [])
s0q1 = [d for d in details if d.get("sample_idx") == 0 and d.get("question_idx") == 1]

if s0q1:
    print(json.dumps(s0q1[0], indent=2))
else:
    print("S0Q1 not found in evaluation_logic_200.json details.")
