import z3
from typing import Any, Dict, List, Tuple
from src.logic.reasoning.parser import parse_formulas
from src.data.cleaning.formatter import standardize_fol_formula


def validate_sample_fol(formulas: List[str]) -> Tuple[bool, str]:
    """Validate a set of FOL formulas using Z3 parser and solver compatibility check."""
    if not formulas:
        return False, "No FOL formulas found in the sample."

    try:
        standardized = [standardize_fol_formula(f) for f in formulas]
        symbols, exprs = parse_formulas(standardized)
        solver = z3.Solver()
        solver.set("timeout", 5000)  # 5-second safety timeout
        for expr in exprs:
            solver.add(expr)
        solver.check()
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_dataset(
    dataset: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate an entire list of unified samples.
    Returns a tuple of (valid_samples, invalid_samples).
    """
    valid_samples = []
    invalid_samples = []

    for sample in dataset:
        nl = sample.get("premises-NL", [])
        fol = sample.get("premises-FOL", [])

        # Check that the number of natural language premises matches the number of FOL formulas
        if len(nl) != len(fol):
            bad_sample = sample.copy()
            bad_sample["validation_error"] = (
                f"Mismatched premise counts: premises-NL has {len(nl)} elements, "
                f"but premises-FOL has {len(fol)} elements."
            )
            invalid_samples.append(bad_sample)
            continue

        is_valid, error_msg = validate_sample_fol(fol)
        if is_valid:
            clean_sample = sample.copy()
            clean_sample.pop("validation_error", None)
            valid_samples.append(clean_sample)
        else:
            bad_sample = sample.copy()
            bad_sample["validation_error"] = error_msg
            invalid_samples.append(bad_sample)

    return valid_samples, invalid_samples
