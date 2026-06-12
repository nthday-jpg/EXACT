import re
from src.utils.normalization import normalize_physics_input


def format_scientific(val: float) -> str:
    s = f"{val:.15g}"
    if "e" in s:
        base, exp = s.split("e")
        exp = int(exp)
        return f"{base}e{exp}"
    return s


def preprocess(text: str) -> str:
    """
    Apply normalization and convert input to SI base units.
    Correctly scales exponential units (e.g., cm^2 to m^2) and preserves
    mathematical context for the fine-tuned 8B router and math solver.
    """
    text = normalize_physics_input(text)

    # IMPROVED REGEX PATTERN:
    # 1. Captures negative and multi-digit exponents (e.g., ^-1, ^2).
    # 2. Explicitly allows greek omega (Ω) and unit combinations like Hz.
    pattern = (
        r"(?<![a-zA-Z])"
        r"(\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*"
        r"(\\[mM]u|μ|µ|mu|u|[TGMkdcmunp])?"
        r"([A-Z][a-zA-Z]*|m|s|g|Ω)"
        r"(?:\^?([+-]?\d+))?\b"
    )

    def repl(match):
        val_str, prefix_raw, unit, exp_str = match.groups()
        val = float(val_str)
        exp = int(exp_str) if exp_str else 1

        prefix_clean = prefix_raw.replace("\\", "") if prefix_raw else ""
        if prefix_clean in ("mu", "Mu", "μ", "µ", "u"):
            multiplier = 1e-6
        elif prefix_clean == "T":
            multiplier = 1e12
        elif prefix_clean == "G":
            multiplier = 1e9
        elif prefix_clean == "M":
            multiplier = 1e6
        elif prefix_clean == "k":
            multiplier = 1e3
        elif prefix_clean == "d":
            multiplier = 1e-1
        elif prefix_clean == "c":
            multiplier = 1e-2
        elif prefix_clean == "m":
            multiplier = 1e-3
        elif prefix_clean == "n":
            multiplier = 1e-9
        elif prefix_clean == "p":
            multiplier = 1e-12
        else:
            multiplier = 1.0

        true_multiplier = multiplier ** abs(exp)

        if unit == "g":
            true_val = val * true_multiplier * (1e-3 ** abs(exp))
            unit_out = "kg" if exp == 1 else f"kg^{exp}"
            return f"{format_scientific(true_val)} {unit_out}"

        if unit in ("Ω", "ohm", "Ohm", "ohms"):
            unit_out = "ohm"
        elif unit.lower() == "hertz" or unit == "Hz":
            unit_out = "Hz"
        else:
            unit_out = unit if exp == 1 else f"{unit}^{exp}"

        true_val = val * true_multiplier
        return f"{format_scientific(true_val)} {unit_out}"

    text = re.sub(pattern, repl, text)
    return text
