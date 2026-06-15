from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


_ENGINEERING_PREFIXES = {
    12: "T",
    9: "G",
    6: "M",
    3: "k",
    0: "",
    -1: "d",
    -2: "c",
    -3: "m",
    -6: "u",
    -9: "n",
    -12: "p",
}

_PREFIX_EXPONENTS = {
    prefix: exp for exp, prefix in _ENGINEERING_PREFIXES.items() if prefix
}

# Whitelist of known base units to prevent incorrect prefix parsing
BASE_UNITS = {
    "m", "g", "s", "A", "V", "F", "N", "J", "W", "Pa", "C",
    "T", "H", "Hz", "ohm", "mol", "cd", "rad", "sr", "K",
    "Wb", "lm", "lx", "Bq", "Gy", "Sv", "kat", "eV", "Da",
}

_SCI_PATTERN = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))[eE]([+-]?\d+)$"
)
_SIMPLE_UNIT_PATTERN = re.compile(r"^([A-Za-z]+)(?:\^(\d+))?$")


def postprocess_answer(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert e-notation answers into engineering-prefix units when possible."""
    if not isinstance(payload, dict):
        return payload

    ans = payload.get("ans")
    unit = payload.get("unit")

    # Handle unit broadcasting: single unit with multiple values
    if isinstance(ans, list) and isinstance(unit, list):
        if len(unit) == 1 and len(ans) > 1:
            unit = unit * len(ans)

    if isinstance(ans, list):
        if isinstance(unit, list):
            if len(unit) != len(ans):
                return payload
            converted = [_convert_value_unit(a, u) for a, u in zip(ans, unit)]
            new_ans, new_unit = zip(*converted) if converted else ([], [])
            return {**payload, "ans": list(new_ans), "unit": list(new_unit)}

        converted = [_convert_value_unit(a, unit) for a in ans]
        new_ans, new_unit = zip(*converted) if converted else ([], [])
        return {**payload, "ans": list(new_ans), "unit": list(new_unit)}

    if isinstance(unit, list):
        if len(unit) != 1:
            return payload
        unit_value = unit[0]
        new_ans, new_unit = _convert_value_unit(ans, unit_value)
        return {**payload, "ans": new_ans, "unit": [new_unit]}

    new_ans, new_unit = _convert_value_unit(ans, unit)
    return {**payload, "ans": new_ans, "unit": new_unit}


def _score_candidate(coeff: Decimal) -> Tuple[int, Decimal]:
    """Score a coefficient for prefix selection.
    
    Prefer coefficients in range [1, 1000), with values near 100 being best.
    """
    coeff = abs(coeff)
    
    if 1 <= coeff < 1000:
        return (0, abs(coeff - 100))
    
    return (1, coeff)


def _convert_value_unit(value: Any, unit: Any) -> Tuple[Any, Any]:
    unit_text = str(unit or "")
    parsed = _parse_simple_unit(unit_text)
    if not parsed:
        return value, unit

    prefix, base_unit, power = parsed
    if prefix:
        return value, unit

    sci = _parse_scientific_value(value)
    if sci is None:
        return value, unit

    coeff, exp10 = sci
    
    # Handle zero values early to avoid ambiguous prefix selection
    if coeff == 0:
        return "0", unit
    
    if power <= 0:
        return value, unit

    # Filter allowed prefixes based on base unit
    # c (centi) and d (deci) are only used with meters in physics
    allowed_exponents = list(_ENGINEERING_PREFIXES.keys())
    if base_unit.lower() != "m":
        # Exclude -1 (d/deci) and -2 (c/centi) for non-meter units
        allowed_exponents = [exp for exp in allowed_exponents if exp not in (-1, -2)]

    # Use coefficient-based selection instead of exponent-distance
    # This produces more natural units, especially for squared/cubed quantities
    # Use Decimal to avoid float precision issues
    coeff_decimal = Decimal(str(coeff))
    
    best_prefix_exp = None
    best_score = None

    for prefix_exp in allowed_exponents:
        shift = exp10 - prefix_exp * power
        coeff_new = coeff_decimal * (Decimal(10) ** shift)
        
        score = _score_candidate(coeff_new)
        
        if best_score is None or score < best_score:
            best_score = score
            best_prefix_exp = prefix_exp

    if best_prefix_exp is None:
        return value, unit
    
    prefix_out = _ENGINEERING_PREFIXES.get(best_prefix_exp)
    if prefix_out is None:
        return value, unit

    # Calculate final coefficient using Decimal for precision
    shift = exp10 - best_prefix_exp * power
    coeff_final = coeff_decimal * (Decimal(10) ** shift)

    unit_out = f"{prefix_out}{base_unit}"
    if power != 1:
        unit_out = f"{unit_out}^{power}"
    return _format_coeff(coeff_final), unit_out


def _parse_simple_unit(unit: str) -> Optional[Tuple[str, str, int]]:
    match = _SIMPLE_UNIT_PATTERN.match(unit)
    if not match:
        return None

    unit_body, power_text = match.groups()
    power = int(power_text) if power_text else 1
    if not unit_body:
        return None

    # Use whitelist to avoid incorrect prefix parsing (e.g., "mol" -> "m" + "ol")
    prefix = ""
    base_unit = unit_body
    
    if len(unit_body) > 1:
        # Try prefixes in order of length (longest first)
        for candidate_prefix in sorted(_PREFIX_EXPONENTS, key=len, reverse=True):
            if unit_body.startswith(candidate_prefix):
                candidate_base = unit_body[len(candidate_prefix):]
                if candidate_base in BASE_UNITS:
                    prefix = candidate_prefix
                    base_unit = candidate_base
                    break

    return prefix, base_unit, power


def _parse_scientific_value(value: Any) -> Optional[Tuple[float, int]]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        text = f"{value:.15g}"
        if "e" not in text and "E" not in text:
            return None
        match = _SCI_PATTERN.match(text)
    else:
        text = str(value).strip()
        if "e" not in text and "E" not in text:
            return None
        match = _SCI_PATTERN.match(text)

    if not match:
        return None

    coeff = float(match.group(1))
    exp = int(match.group(2))
    return coeff, exp


def _format_coeff(value: Decimal) -> str:
    """Format a Decimal coefficient, preserving precision.
    
    Uses scientific notation for extreme magnitudes to avoid
    extremely long strings of zeros.
    """
    if value == 0:
        return "0"
    
    # Check magnitude to decide formatting
    magnitude = value.adjusted()
    
    # Use scientific notation for very large or very small magnitudes
    if magnitude > 15 or magnitude < -15:
        return f"{value.normalize():E}"
    
    # Use fixed-point notation for reasonable magnitudes
    text = format(value.normalize(), "f")
    
    # Strip trailing zeros and decimal point if present
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    
    return text
