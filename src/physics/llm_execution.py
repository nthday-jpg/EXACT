"""Utilities for executing LLM-generated physics code and scaling results."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import sympy as sp


def parse_model_json(model_content: str) -> Dict[str, Any]:
    """Parse raw model content into a JSON dict."""
    return json.loads(model_content.strip())


def execute_llm_code(
    model_content: str,
    *,
    precision: int = 4,
) -> Tuple[list[Any], Optional[list[str]]]:
    """Execute model code and format numeric answers in SI base units.

    Expected keys in the model JSON:
    - python_code: code that sets `ans` in base SI units
    """
    model_json = parse_model_json(model_content)
    python_code = model_json.get("python_code")

    if not python_code:
        return None, None

    local_vars: Dict[str, Any] = {}
    exec(python_code, {"sp": sp, "sympy": sp}, local_vars)

    raw_ans = local_vars.get("ans")
    if raw_ans is None:
        return None, None

    base_unit = local_vars.get("unit") or [""]

    def _format_scientific(val: float) -> str:
        abs_val = abs(val)
        if abs_val != 0.0 and (abs_val < 1e-3 or abs_val >= 1e4):
            s = f"{val:.{precision}e}"
        else:
            s = f"{val:.{precision}g}"

        if "e" in s:
            base, exp = s.split("e")
            exp = int(exp)
            return f"{base}e{exp}"
        return s

    def _format_value(val: Any) -> Any:
        try:
            evaluated = sp.N(val)
            if evaluated.is_number:
                numeric_val = float(evaluated)
                return _format_scientific(numeric_val)
        except (TypeError, ValueError):
            pass
        return str(val)

    if isinstance(raw_ans, list):
        formatted_list = [_format_value(v) for v in raw_ans]
        return formatted_list, base_unit

    return [_format_value(raw_ans)], base_unit
