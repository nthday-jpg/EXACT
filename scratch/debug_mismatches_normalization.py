import json
import sys
from pathlib import Path
import re

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.utils.normalization import normalize_logic_fol_entry, unify_fol_predicates

with open(root / "data" / "fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

print(f"Total failed cases: {len(failed_cases)}")

count = 0
for item in failed_cases:
    gt = item.get("premises-FOL-GT", [])
    pred = item.get("premises-FOL-Pred", [])
    
    if not gt or not pred or len(gt) != len(pred):
        continue
        
    norm_pred = [normalize_logic_fol_entry(x) for x in pred]
    norm_gt = [normalize_logic_fol_entry(x) for x in gt]
    
    all_fol = norm_pred + norm_gt
    unified_all = unify_fol_predicates(all_fol)
    unified_pred = [x.strip() for x in unified_all[:len(norm_pred)]]
    unified_gt = [x.strip() for x in unified_all[len(norm_pred):]]
    
    if unified_pred != unified_gt:
        count += 1
        if count <= 5:
            print(f"\n--- Example ID: {item.get('example_id')} ---")
            print("NL premises:")
            for p in item.get("premises-NL", []):
                print(f"  - {p}")
            print("\nGT Raw vs Pred Raw:")
            for g, p in zip(gt, pred):
                print(f"  GT:   {g}")
                print(f"  Pred: {p}")
            print("\nGT Unified vs Pred Unified:")
            for ug, up in zip(unified_gt, unified_pred):
                diff_char = "" if ug == up else "  <-- MISMATCH"
                print(f"  GT_U:   {ug}")
                print(f"  Pred_U: {up}{diff_char}")
            print("-" * 50)
        
print(f"Printed {count} mismatched examples.")
