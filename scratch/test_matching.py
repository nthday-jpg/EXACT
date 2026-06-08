import json
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.utils.normalization import normalize_logic_fol_entry, unify_fol_predicates

# Load failed cases
with open(root / "data" / "fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

print(f"Total failed cases to check: {len(failed_cases)}")

matched_count = 0
for idx, item in enumerate(failed_cases):
    gt = item.get("premises-FOL-GT", [])
    pred = item.get("premises-FOL-Pred", [])
    
    if not gt or not pred or len(gt) != len(pred):
        continue
        
    # Standard exact match check (raw strings)
    raw_match = [str(x).strip() for x in pred] == [str(x).strip() for x in gt]
    
    # Normalized exact match check
    norm_pred = [normalize_logic_fol_entry(x) for x in pred]
    norm_gt = [normalize_logic_fol_entry(x) for x in gt]
    
    all_fol = norm_pred + norm_gt
    unified_all = unify_fol_predicates(all_fol)
    unified_pred = [x.strip() for x in unified_all[:len(norm_pred)]]
    unified_gt = [x.strip() for x in unified_all[len(norm_pred):]]
    
    norm_match = unified_pred == unified_gt
    
    if norm_match:
        matched_count += 1
        if matched_count <= 5:
            print(f"\n--- Match {matched_count} (Example ID: {item.get('example_id')}) ---")
            print("NL premises:")
            for p in item.get("premises-NL", [])[:3]:
                print(f"  - {p}")
            print("GT Raw:", gt)
            print("Pred Raw:", pred)
            print("GT Unified:", unified_gt)
            print("Pred Unified:", unified_pred)

print(f"\nTotal that would match under normalization and unification: {matched_count} / {len(failed_cases)}")
