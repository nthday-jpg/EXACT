import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas
from scripts.validate_dataset_syntax import validate_sample_fol

with open(root / "data" / "processed" / "logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

val_samples = [item for item in data if item.get("split") == "val"]
print(f"Total validation samples: {len(val_samples)}")

invalid_count = 0
for item in val_samples:
    eid = item.get("example_id")
    fol = item.get("premises-FOL", [])
    
    is_valid, err = validate_sample_fol(fol)
    if not is_valid:
        invalid_count += 1
        print(f"Example ID: {eid} is INVALID:")
        print(f"  Error: {err}")
        print("  Formulas:")
        for f in fol:
            print(f"    - {f}")
        print("-" * 50)

print(f"Verification completed. Invalid validation samples: {invalid_count} / {len(val_samples)}")
