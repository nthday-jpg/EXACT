import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
partial_path = root / "scratch" / "translation_inspections_partial.json"

if not partial_path.exists():
    print("No partial progress found yet.")
    sys.exit(0)

with open(partial_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total evaluated samples: {len(data)}")

verdicts = {}
for k, v in data.items():
    verdict = v.get("verdict", "unknown")
    verdicts[verdict] = verdicts.get(verdict, 0) + 1

print("Verdict distribution:")
for k, v in verdicts.items():
    pct = (v / len(data)) * 100
    print(f"  - {k}: {v} ({pct:.2f}%)")
