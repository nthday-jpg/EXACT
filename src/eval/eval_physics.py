"""Evaluation helpers for physics dataset answers."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import sympy as sp
import pint
from dotenv import load_dotenv

# Instantiate the UnitRegistry globally to prevent object comparison clashes
ureg = pint.UnitRegistry()

# Load environment variables from .env file
try:
    load_dotenv()
except ImportError:
    print(
        "Warning: python-dotenv not installed, ensure environment variables are set manually."
    )


_PHYSICS_EVAL_ENV_NOTICE_EMITTED = False

_PREFIX_FACTORS = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "c": 1e-2,
    "d": 1e-1,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}

# Macro conversions for basic unit equivalencies
_UNIT_EQUIV = {"v/m": "V/m", "n/c": "V/m", "V/M": "V/m", "N/C": "V/m"}


@dataclass(frozen=True)
class _Item:
    value: Any
    unit: str
    raw_value: str  # Kept to extract structural features like sig-figs later


def evaluate_physics_answer(
    question: str,
    model_answer: Any,
    model_raw_output: Optional[str],
    correct_answer: Any,
    *,
    llm_model: Optional[str] = None,
) -> bool:
    """Core evaluation pipeline entry point."""
    if model_answer is None or correct_answer is None:
        return False

    model_items = _normalize_items(model_answer)
    correct_items = _normalize_items(correct_answer)

    if not model_items or not correct_items:
        return False

    return _compare_item_sets(
        question, model_items, correct_items, model_raw_output, llm_model=llm_model
    )


def _clean_micro_symbols(unit_str: str) -> str:
    """Maps various micro configurations cleanly to standard 'u'."""
    return (
        unit_str.replace("μ", "u")
        .replace("mu", "u")
        .replace("Micro", "u")
        .replace("micro", "u")
    )


def _normalize_unit(unit: str) -> str:
    """Normalizes unit strings while strictly preserving metric case sensitivity."""
    if not unit:
        return ""
    unit = unit.strip().strip("[]()\"'")
    if unit in ["-", "—", "text", "None", "none", ""]:
        return ""

    # Check map using matching case or standardized equivalents
    if unit in _UNIT_EQUIV:
        return _UNIT_EQUIV[unit]
    if unit.lower() in _UNIT_EQUIV:
        return _UNIT_EQUIV[unit.lower()]

    return unit


def _to_number(value: Any) -> Optional[float]:
    """Safely converts input types to floats if they represent numeric expressions."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, sp.Number):
        return float(value.evalf())
    if isinstance(value, str):
        value_clean = value.strip().replace("{", "").replace("}", "")
        # Handle simple LaTeX fraction strings if encountered
        if "frac" in value_clean:
            match = re.search(
                r"frac\s*([-+]?\d*\.?\d+)\s*([-+]?\d*\.?\d+)",
                value_clean.replace("\\", ""),
            )
            if match:
                try:
                    return float(match.group(1)) / float(match.group(2))
                except ZeroDivisionError:
                    return None
        # Handle scientific notation format like 33.6 * 10^5
        if "*" in value_clean or "x" in value_clean:
            value_clean = re.sub(r"x\s*10\s*\^", "e", value_clean)
            value_clean = re.sub(r"\*\s*10\s*\^", "e", value_clean)
            value_clean = re.sub(r"x\s*10\s*\*+", "e", value_clean)
            value_clean = re.sub(r"\*\s*10\s*\*+", "e", value_clean)
        try:
            return float(sp.sympify(value_clean).evalf())
        except Exception:
            # Fallback regex extraction for messy numeric strings
            match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", value_clean)
            if match:
                try:
                    return float(match.group(0))
                except Exception:
                    return None
    return None


def _convert_to_si(value: float, unit: str) -> Tuple[float, str]:
    """Converts value to base SI units dynamically using Pint."""
    unit = _normalize_unit(unit)
    if not unit:
        return value, unit
    try:
        # Pass unit directly to case-sensitive registry
        quantity = value * ureg(unit)
        quantity = quantity.to_base_units()
        return float(quantity.magnitude), str(quantity.units)
    except Exception:
        # Fallback tracking using standard metric maps if Pint fails standard validation
        for prefix, factor in _PREFIX_FACTORS.items():
            if unit.startswith(prefix) and len(unit) > len(prefix):
                base_unit = unit[len(prefix) :]
                return value * factor, base_unit
    return value, unit


def _coerce_value(value: Any, unit: str) -> Tuple[Any, str]:
    """Extracts numeric values and resolves them to baseline scales."""
    numeric = _to_number(value)
    if numeric is None:
        return value, _normalize_unit(unit)
    scaled_val, scaled_unit = _convert_to_si(numeric, unit)
    return scaled_val, scaled_unit


def _normalize_items(payload: dict | list | str | Any) -> List[_Item]:
    """Flattens incoming payload distributions into clean evaluable _Item sets."""
    processed_items = []

    if isinstance(payload, dict):
        ans_field = (
            payload.get("ans")
            or payload.get("model_answer")
            or payload.get("correct_answer")
        )
        unit_field = payload.get("unit") or ""

        if ans_field is not None:
            if isinstance(ans_field, list) and isinstance(unit_field, list):
                for a, u in zip(ans_field, unit_field):
                    processed_items.extend(_normalize_items({"ans": a, "unit": u}))
                return processed_items
            elif isinstance(ans_field, list):
                for a in ans_field:
                    processed_items.extend(
                        _normalize_items({"ans": a, "unit": unit_field})
                    )
                return processed_items
            payload = {"ans": ans_field, "unit": unit_field}

    if isinstance(payload, dict) and "ans" in payload:
        v = payload["ans"]
        u = payload.get("unit") or ""
        cleaned_unit = _clean_micro_symbols(str(u or ""))
        final_value, final_unit = _coerce_value(v, cleaned_unit)
        cleaned_raw = str(v).strip()
        processed_items.append(
            _Item(value=final_value, unit=final_unit, raw_value=cleaned_raw)
        )
        return processed_items

    if isinstance(payload, list):
        for item in payload:
            processed_items.extend(_normalize_items(item))
        return processed_items

    # Flat primitive fallback encapsulation
    cleaned_raw = str(payload).strip()
    final_value, final_unit = _coerce_value(payload, "")
    processed_items.append(
        _Item(value=final_value, unit=final_unit, raw_value=cleaned_raw)
    )
    return processed_items


def _maybe_sympy_expr(value: Any) -> Optional[sp.Expr]:
    """Parses expressions into valid SymPy trees, permitting multi-character variables."""
    if isinstance(value, sp.Expr):
        return value
    if not isinstance(value, str):
        return None
    try:
        # Removed text filter logic that blocked multi-character terms like 'q0' or 'ke'
        cleaned = value.strip().replace("{", "").replace("}", "").replace("\\", "")
        return sp.sympify(cleaned)
    except Exception:
        return None


def _get_sig_figs(raw_val: str) -> Optional[int]:
    """Extracts precision sig-figs from raw answer strings."""
    s = raw_val.strip().lower()
    s = re.sub(r"^[+-]", "", s)
    if "e" in s:
        s = s.split("e")[0]
    s = s.replace(".", "")
    s = s.lstrip("0")
    if not s:
        return None
    return len(s)


def _numeric_match(model_item: _Item, correct_item: _Item) -> bool:
    """Performs precision validation across numeric properties."""
    try:
        model_val = float(model_item.value)
        correct_val = float(correct_item.value)
    except (ValueError, TypeError):
        return False

    if model_item.unit != correct_item.unit:
        return False

    if correct_val == 0.0:
        return abs(model_val) < 1e-7

    # Relative error fallback
    rel_err = abs(model_val - correct_val) / abs(correct_val)
    if rel_err <= 0.02:  # Tolerates minor rounding differences (up to 2%)
        return True

    # Check via explicit significant figures match
    sig_figs = _get_sig_figs(correct_item.raw_value)
    if sig_figs:
        try:
            factor = 10 ** (math.floor(math.log10(abs(correct_val))) - (sig_figs - 1))
            return abs(model_val - correct_val) <= (factor * 1.05)
        except Exception:
            pass

    return False


def _symbolic_match(model_item: _Item, correct_item: _Item) -> bool:
    """Evaluates algebraic equation sets for structural zero-equivalence."""
    expr_model = _maybe_sympy_expr(model_item.value)
    expr_correct = _maybe_sympy_expr(correct_item.value)

    if expr_model is None or expr_correct is None:
        return False

    try:
        diff = sp.simplify(expr_model - expr_correct)
        if diff == 0:
            return True
        # Numeric structural check for non-zero constants
        if diff.is_number:
            return abs(float(diff.evalf())) < 1e-5
    except Exception:
        pass
    return False


def _find_match_index(remaining_model: List[_Item], correct_item: _Item) -> int:
    """Locates matching item index across categorical validation layers."""
    # Layer 1: Accurate numerical evaluations
    for i, m_item in enumerate(remaining_model):
        if _numeric_match(m_item, correct_item):
            return i

    # Layer 2: Algebraic equivalence checks
    for i, m_item in enumerate(remaining_model):
        if _symbolic_match(m_item, correct_item):
            return i

    # Layer 3: String match fallback
    for i, m_item in enumerate(remaining_model):
        if str(m_item.value).strip().lower() == str(correct_item.value).strip().lower():
            return i

    return -1


def _compare_item_sets(
    question: str,
    model_items: List[_Item],
    correct_items: List[_Item],
    model_raw_output: Optional[str] = None,
    llm_model: Optional[str] = None,
) -> bool:
    """Compares the evaluation answer arrays with matching safeguards."""
    remaining = model_items[:]
    matched_count = 0

    for correct_item in correct_items:
        match_idx = _find_match_index(remaining, correct_item)
        if match_idx != -1:
            remaining.pop(match_idx)
            matched_count += 1
        else:
            # If an exact match wasn't found, try an item-level LLM check if available
            is_numeric = isinstance(correct_item.value, (int, float))

            if llm_model and not is_numeric:
                for i, m_item in enumerate(remaining):
                    if _llm_or_text_match(
                        question, str(m_item.value), str(correct_item.value), llm_model
                    ):
                        remaining.pop(i)
                        matched_count += 1
                        break

    if matched_count == len(correct_items):
        return True

    # Final block check: only do this if the answers are primarily text
    # (If the correct answer is a list of numbers, we shouldn't be here)
    all_text = all(not isinstance(i.value, (int, float)) for i in correct_items)
    if all_text:
        model_text = " ".join([str(i.value) for i in model_items])
        correct_text = " ".join([str(i.value) for i in correct_items])
        return _llm_or_text_match(
            question=question,
            model_text=model_text,
            model_raw_output=model_raw_output,
            correct_text=correct_text,
            llm_model=llm_model,
        )

    return False


def _llm_or_text_match(
    question: str,
    model_text: str,
    correct_text: str,
    model_raw_output: Optional[str] = None,
    llm_model: Optional[str] = None,
) -> bool:
    """Final fallback checking for qualitative plain text equivalencies."""
    norm_model = _normalize_text(model_text)
    norm_correct = _normalize_text(correct_text)

    clean_model = re.sub(r"^[a-zA-Z_]\s*[:=]\s*", "", norm_model).strip()
    clean_correct = re.sub(r"^[a-zA-Z_]\s*[:=]\s*", "", norm_correct).strip()

    try:
        num_model = re.sub(r"[^0-9.\-eE]", "", clean_model)
        num_correct = re.sub(r"[^0-9.\-eE]", "", clean_correct)

        if num_model and num_correct:
            v1 = float(num_model)
            v2 = float(num_correct)
            if abs(v1 - v2) <= 0.01 * abs(v2):
                return True
    except ValueError:
        pass

    if clean_model == clean_correct:
        return True

    if len(clean_correct) > 3 and (
        clean_model in clean_correct or clean_correct in clean_model
    ):
        return True

    if (
        clean_model == clean_correct
        or clean_model in clean_correct
        or clean_correct in clean_model
    ):
        return True

    try:
        from src.llm.llm_client import LLMClient

        api_key = os.getenv("PHYSICS_EVAL_LLM_KEY", "")
        llm_model = llm_model or os.getenv("PHYSICS_EVAL_LLM_MODEL", "gemini-3.5-flash")
        system_prompt = (
            "You are a strict physics evaluation assistant. Your task is to determine if a 'Model Answer' "
            "is semantically equivalent to the 'Correct Answer' for the given question.\n\n"
            "### EXTRACTION & PARSING RULE:\n"
            "- Check 'Model Answer (parsed)'. If it is None, 'null', or empty, inspect the 'Model Raw Output (fallback context)' string.\n"
            "- Look inside the 'python_code' array or the text blocks within that raw output to extract the text intended as the answer (e.g., ans = [...]).\n"
            "- Evaluate this extracted text against the Correct Answer. Do not fail a model due to formatting mismatches or empty parsed fields if the answer is present in the raw output.\n\n"
            "### SEMANTIC EQUIVALENCE RULES (ELECTROMAGNETISM & AC/LC CIRCUITS):\n"
            "1. CONCEPTUAL SHORTHAND: Treat core components, fields, or regions where physics behavior is localized as equivalent to detailed geometric descriptions (e.g., 'within the interior along its central axis' IS equivalent to 'inside the solenoid').\n"
            "2. PHYSICAL TRIGGERS: For induction phenomena, descriptions specifying changing linked fields vs. changing sources are physically equivalent triggers (e.g., 'changing magnetic flux' is equivalent to 'changing current' for a self-inducing coil).\n"
            "3. PROPORTIONALITY & DIRECTION: Directional vectors/trends ('increases') match direct linear relations ('increases in direct proportion') unless a non-linear exponent scaling (like squared) is explicitly stated or violated.\n"
            "4. PERMISSIBLE EXTRAS: Including a fundamental physical constant (e.g., 'permeability of free space') alongside an otherwise perfect list of geometric variables does not invalidate the answer.\n\n"
            "### OUTPUT FORMAT GUIDELINE:\n"
            "You must structure your response exactly as follows:\n"
            "1. Start with a '<thinking>' tag.\n"
            "2. Break down your reasoning step-by-step: compare the core physics concepts, verify parsing fallback rules, and map the answers against the 4 semantic equivalence rules.\n"
            "3. Close the '</thinking>' tag.\n"
            "4. On a brand new line, provide your final judgment. This must be EXACTLY 'Final Verdict: yes' or 'Final Verdict: no' with no punctuation or extra text.\n\n"
            "Example Output Format:\n"
            "<thinking>\n"
            "[Your step-by-step physics assessment goes here...]\n"
            "</thinking>\n"
            "Final Verdict: yes"
        )

        client = LLMClient(
            model_name=llm_model, api_key=api_key, system_prompt=system_prompt
        )
        user_prompt = (
            f"Question asked to the model: {question}\n"
            f"Correct Answer template: {correct_text}\n"
            f"Model Answer (parsed): {model_text}\n"
            f"Model Raw Output (fallback context): {model_raw_output}\n"
            f"Are they semantically equivalent based on physics principles? Reply ONLY with 'yes' or 'no'."
        )
        response = client.generate_text(user_prompt)
        final_verdict = response.split("Final Verdict:")[-1].strip().lower()
        return True if final_verdict.startswith("yes") else False
    except Exception as e:
        print(f"Error occurred during LLM evaluation: {e}")
        return False


def _normalize_text(text: str) -> str:
    """Normalizes qualitative texts by removing filler words and formatting anomalies."""
    text = text.lower()
    text = text.replace("in the coil", "").replace("of the coil", "")
    text = text.replace("stored entirely in", "").replace("stored in", "")
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())
