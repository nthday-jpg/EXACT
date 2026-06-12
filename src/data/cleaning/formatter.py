from src.utils.normalization import normalize_logic_fol_entry


def standardize_fol_formula(f_str: str) -> str:
    """Standardize logical operators and balance parentheses in an FOL formula string."""
    return normalize_logic_fol_entry(f_str)
