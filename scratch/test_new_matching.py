import json
import sys
from pathlib import Path
import re

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.utils.normalization import normalize_logic_fol_entry, unify_fol_predicates

def test_new_matching():
    with open(root / "data" / "fol_failed_cases.json", "r", encoding="utf-8") as f:
        failed_cases = json.load(f)

    with open(root / "data" / "processed" / "logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
        val_data = json.load(f)

    # Build a map from example_id to new GT FOL formulas
    new_gt_map = {}
    for item in val_data:
        eid = item.get("example_id")
        if eid:
            new_gt_map[eid] = item.get("premises-FOL", [])
            # Also register without _canonical if canonicalized
            if eid.endswith("_canonical"):
                new_gt_map[eid.split("_canonical")[0]] = item.get("premises-FOL", [])
            else:
                new_gt_map[f"{eid}_canonical"] = item.get("premises-FOL", [])

    print(f"Total failed cases loaded: {len(failed_cases)}")

    raw_matches = 0
    norm_matches = 0
    missing_gt = 0
    len_mismatch = 0
    formula_diffs = 0

    for idx, item in enumerate(failed_cases):
        eid = item.get("example_id")
        pred = item.get("premises-FOL-Pred", [])
        
        # Get the new cleaned GT
        new_gt = new_gt_map.get(eid, [])
        if not new_gt:
            # Try splitting by _canonical or underscore if there's any mismatch
            base_eid = eid.split("_")[0]
            # Try prefix match
            for k in new_gt_map:
                if k.startswith(base_eid) and len(new_gt_map[k]) == len(pred):
                    new_gt = new_gt_map[k]
                    break

        if not new_gt:
            missing_gt += 1
            continue

        if len(pred) != len(new_gt):
            len_mismatch += 1
            continue

        # Standard exact match (stripped)
        pred_stripped = [str(x).strip() for x in pred]
        gt_stripped = [str(x).strip() for x in new_gt]
        
        is_raw_match = pred_stripped == gt_stripped
        if is_raw_match:
            raw_matches += 1

        # Normalized exact match check
        norm_pred = [normalize_logic_fol_entry(x) for x in pred]
        norm_gt = [normalize_logic_fol_entry(x) for x in new_gt]
        
        all_fol = norm_pred + norm_gt
        unified_all = unify_fol_predicates(all_fol)
        unified_pred = [x.strip() for x in unified_all[:len(norm_pred)]]
        unified_gt = [x.strip() for x in unified_all[len(norm_pred):]]
        
        is_norm_match = unified_pred == unified_gt
        if is_norm_match:
            norm_matches += 1
        else:
            formula_diffs += 1
            if formula_diffs <= 3:
                print(f"\nMismatch {formula_diffs} (ID: {eid})")
                print("Pred Unified:", unified_pred)
                print("GT Unified:  ", unified_gt)

    print(f"\n=== Debug Stats ===")
    print(f"Missing GT: {missing_gt}")
    print(f"Length mismatch: {len_mismatch}")
    print(f"Formula mismatch: {formula_diffs}")
    print(f"Raw matches: {raw_matches}")
    print(f"Normalized matches: {norm_matches}")

if __name__ == "__main__":
    test_new_matching()
