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
    
    # Matches a number, optional space, prefix, and unit.
    # Excludes matching if preceded by a letter to avoid part of a word.
    pattern = r"(?<![a-zA-Z])(\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*(\\[mM]u|μ|mu|[TGMkcmnpf])([A-Z][a-zA-Z]*|m|s|g)\b"
    
    def repl(match):
        val_str, prefix_raw, unit = match.groups()
        val = float(val_str)
        
        prefix_clean = prefix_raw.replace("\\", "")
        if prefix_clean in ("mu", "Mu", "μ"):
            multiplier = 1e-6
        elif prefix_clean == "T":
            multiplier = 1e12
        elif prefix_clean == "G":
            multiplier = 1e9
        elif prefix_clean == "M":
            multiplier = 1e6
        elif prefix_clean == "k":
            multiplier = 1e3
        elif prefix_clean == "c":
            multiplier = 1e-2
        elif prefix_clean == "m":
            multiplier = 1e-3
        elif prefix_clean == "n":
            multiplier = 1e-9
        elif prefix_clean == "p":
            multiplier = 1e-12
        elif prefix_clean == "f":
            multiplier = 1e-15
        else:
            multiplier = 1.0
            
        if unit == "g":
            # the SI base unit for mass is kg
            true_val = val * multiplier * 1e-3
            return f"{format_scientific(true_val)} kg"
            
        return f"{format_scientific(val * multiplier)} {unit}"
        
    text = re.sub(pattern, repl, text)
    return text
