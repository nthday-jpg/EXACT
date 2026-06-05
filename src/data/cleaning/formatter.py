import re


def standardize_fol_formula(f_str: str) -> str:
    """Standardize logical operators and balance parentheses in an FOL formula string."""
    f_clean = f_str.strip()
    f_clean = (
        f_clean.replace("\u00ac", "NOT ")
        .replace("\u2227", " AND ")
        .replace("\u2228", " OR ")
        .replace("\u2192", " -> ")
        .replace("\u2194", " <-> ")
    )
    f_clean = re.sub(r"\s+", " ", f_clean)
    open_count = f_clean.count("(")
    close_count = f_clean.count(")")
    if close_count < open_count:
        f_clean = f_clean + ")" * (open_count - close_count)
    return f_clean
