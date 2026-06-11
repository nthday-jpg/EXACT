import json
import sys
from pathlib import Path
import re

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas
from src.utils.normalization import normalize_logic_fol_entry, unify_fol_predicates

def check_logical_equivalence(f1_str, f2_str):
    """
    Checks if two FOL formula strings are logically equivalent under Z3.
    """
    try:
        # Standardize and parse the two formulas together
        # so they share the same symbols/casing
        norm1 = normalize_logic_fol_entry(f1_str)
        norm2 = normalize_logic_fol_entry(f2_str)
        
        # We need to unify predicate naming before parsing
        unified = unify_fol_predicates([norm1, norm2])
        u1, u2 = unified[0], unified[1]
        
        symbols, exprs = parse_formulas([u1, u2])
        e1, e2 = exprs[0], exprs[1]
        
        # Check if e1 <-> e2 is a tautology (i.e. NOT (e1 <-> e2) is unsat)
        solver = z3.Solver()
        solver.set("timeout", 1000) # 1s timeout
        solver.add(z3.Not(e1 == e2))
        
        if solver.check() == z3.unsat:
            return True
        else:
            return False
    except Exception as e:
        # If parsing fails or we can't prove, fallback to False
        return False

def test_logical_equivalence():
    with open(root / "data" / "fol_failed_cases.json", "r", encoding="utf-8") as f:
        failed_cases = json.load(f)

    with open(root / "data" / "processed" / "logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
        val_data = json.load(f)

    new_gt_map = {}
    for item in val_data:
        eid = item.get("example_id")
        if eid:
            new_gt_map[eid] = item.get("premises-FOL", [])
            if eid.endswith("_canonical"):
                new_gt_map[eid.split("_canonical")[0]] = item.get("premises-FOL", [])
            else:
                new_gt_map[f"{eid}_canonical"] = item.get("premises-FOL", [])

    print(f"Total failed cases loaded: {len(failed_cases)}")

    equiv_samples = 0
    total_formulas = 0
    equiv_formulas = 0

    for idx, item in enumerate(failed_cases):
        eid = item.get("example_id")
        pred = item.get("premises-FOL-Pred", [])
        
        new_gt = new_gt_map.get(eid, [])
        if not new_gt:
            base_eid = eid.split("_")[0]
            for k in new_gt_map:
                if k.startswith(base_eid) and len(new_gt_map[k]) == len(pred):
                    new_gt = new_gt_map[k]
                    break

        if not new_gt or len(pred) != len(new_gt):
            continue

        sample_equiv = True
        for p_f, g_f in zip(pred, new_gt):
            total_formulas += 1
            is_eq = check_logical_equivalence(p_f, g_f)
            if is_eq:
                equiv_formulas += 1
            else:
                sample_equiv = False

        if sample_equiv:
            equiv_samples += 1
            if equiv_samples <= 3:
                print(f"\n--- Logical Equivalent Sample {equiv_samples} (ID: {eid}) ---")
                print("NL Premises:")
                for p in item.get("premises-NL", []):
                    print(f"  - {p}")
                print("GT FOL:")
                for p in new_gt:
                    print(f"  - {p}")
                print("Pred FOL:")
                for p in pred:
                    print(f"  - {p}")

    print(f"\n=== LOGICAL EQUIVALENCE RESULTS ON PREVIOUS FAILURE CASES ===")
    print(f"Formula-level equivalence rate: {equiv_formulas} / {total_formulas} ({equiv_formulas / total_formulas * 100:.2f}%)")
    print(f"Sample-level equivalence rate (Exact Match): {equiv_samples} / {len(failed_cases)} ({equiv_samples / len(failed_cases) * 100:.2f}%)")

if __name__ == "__main__":
    test_logical_equivalence()
