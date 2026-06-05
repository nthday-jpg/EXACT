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
    Example: '0.3 μC' to '3e-7 C'
    """
    text = normalize_physics_input(text)
    
    # Matches a number, optional space, optional prefix, unit, and optional exponent.
    # Excludes matching if preceded by a letter to avoid part of a word.
    pattern = (
        r"(?<![a-zA-Z])"
        r"(\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*"
        r"(\\[mM]u|μ|µ|mu|u|[TGMkdcmunp])?"
        r"([A-Z][a-zA-Z]*|m|s|g)"
        r"(?:\^?(\d+))?\b"
    )
    
    def repl(match):
        val_str, prefix_raw, unit, exp_str = match.groups()
        val = float(val_str)
        exp = int(exp_str) if exp_str else 1
        
        prefix_clean = prefix_raw.replace("\\", "") if prefix_raw else ""
        if prefix_clean in ("mu", "Mu", "μ", "µ"):
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
        elif prefix_clean in ("u",):
            multiplier = 1e-6
        elif prefix_clean == "n":
            multiplier = 1e-9
        elif prefix_clean == "p":
            multiplier = 1e-12
        else:
            multiplier = 1.0
            
        if exp != 1 and unit != "m":
            return match.group(0)

        if unit == "g":
            # the SI base unit for mass is kg (only for first power)
            true_val = val * multiplier * 1e-3
            return f"{format_scientific(true_val)} kg"
            
        true_val = val * (multiplier ** exp)
        unit_out = unit if exp == 1 else f"{unit}^{exp}"
        return f"{format_scientific(true_val)} {unit_out}"
        
    text = re.sub(pattern, repl, text)
    return text
