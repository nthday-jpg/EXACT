from __future__ import annotations

import re
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
    -6: "μ",
    -9: "n",
    -12: "p",
}

_PREFIX_EXPONENTS = {
    prefix: exp for exp, prefix in _ENGINEERING_PREFIXES.items() if prefix
}

_SCI_PATTERN = re.compile(r"^([+-]?(?:\d+\.\d+|\d+))(?:e([+-]?\d+))$", re.IGNORECASE)
_SIMPLE_UNIT_PATTERN = re.compile(r"^([A-Za-z]+)(?:\^(\d+))?$")


def postprocess_answer(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert e-notation answers into engineering-prefix units when possible."""
    if not isinstance(payload, dict):
        return payload

    ans = payload.get("ans")
    unit = payload.get("unit")

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
    if power <= 0:
        return value, unit

    if exp10 % power != 0:
        return value, unit

    prefix_exp = min(
        _ENGINEERING_PREFIXES.keys(),
        key=lambda exp: abs(exp10 - exp * power),
    )
    prefix_out = _ENGINEERING_PREFIXES.get(prefix_exp)
    if prefix_out is None:
        return value, unit

    coeff = coeff * (10 ** (exp10 - prefix_exp * power))

    unit_out = f"{prefix_out}{base_unit}"
    if power != 1:
        unit_out = f"{unit_out}^{power}"
    return _format_coeff(coeff), unit_out


def _parse_simple_unit(unit: str) -> Optional[Tuple[str, str, int]]:
    match = _SIMPLE_UNIT_PATTERN.match(unit)
    if not match:
        return None

    unit_body, power_text = match.groups()
    power = int(power_text) if power_text else 1
    if not unit_body:
        return None

    prefix = ""
    base_unit = unit_body
    if len(unit_body) > 1:
        maybe_prefix = unit_body[0]
        if maybe_prefix in _PREFIX_EXPONENTS:
            prefix = maybe_prefix
            base_unit = unit_body[1:]

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


def _format_coeff(value: float) -> str:
    if value == 0:
        return "0"
    text = f"{value:.15g}"
    if "e" in text or "E" in text:
        text = f"{value:.15f}"
    # Only strip trailing zeros and the decimal point if there's a decimal part.
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
