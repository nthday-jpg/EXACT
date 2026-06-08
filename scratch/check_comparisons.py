import json
import re
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


root = Path(__file__).resolve().parents[1]
with open(root / "data" / "processed" / "logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Total samples:", len(data))
comparison_samples = []
for item in data:
    if item.get("split") != "train":
        continue
    has_comp = False
    for fol in item.get("premises-FOL", []):
        # Strip implication arrows to avoid matching -> and <->
        fol_clean = fol.replace("<->", "").replace("->", "")
        if any(op in fol_clean for op in [">=", "<=", ">", "<"]):
            has_comp = True
            break

    if has_comp:
        comparison_samples.append(item)

print("Number of training samples containing comparisons:", len(comparison_samples))
for i, item in enumerate(comparison_samples[:5]):
    print(f"\n--- Sample {i+1} (ID: {item.get('example_id')}) ---")
    print("NL Premises:")
    for p in item.get("premises-NL", []):
        print(f"  - {p}")
    print("FOL Premises:")
    for p in item.get("premises-FOL", []):
        print(f"  - {p}")
