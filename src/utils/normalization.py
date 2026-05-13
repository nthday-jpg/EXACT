"""Normalization utilities for the physics QA dataset."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional

# Use unicode escapes to keep the source ASCII-only.
_MINUS_CHARS = "\u2212\u2013\u2014\u207b"  # minus, en dash, em dash, superscript minus
_MULTIPLY_CHARS = "\u00d7\u22c5\u00b7"  # multiplication sign, dot operator, middle dot

_SUPERSCRIPT_TO_ASCII = {
    "\u2070": "0",
    "\u00b9": "1",
    "\u00b2": "2",
    "\u00b3": "3",
    "\u2074": "4",
    "\u2075": "5",
    "\u2076": "6",
    "\u2077": "7",
    "\u2078": "8",
    "\u2079": "9",
    "\u207a": "+",
    "\u207b": "-",
}

_FRACTIONS_ASCII = {
    "\u00bd": "1/2",
    "\u2153": "1/3",
    "\u2154": "2/3",
}

_FRACTIONS_DECIMAL = {
    "1/2": "0.5",
    "1/3": "0.3333333333",
    "2/3": "0.6666666667",
}

_UNIT_NORMALIZATION = {
    "\u03a9": "ohm",
    "meter": "m",
    "meters": "m",
    "second": "s",
    "seconds": "s",
}


def normalize_input(text: str) -> str:
    """Conservative normalization for input prompts."""
    if not text:
        return ""

    text = _normalize_scientific_notation(text)
    text = unicodedata.normalize("NFKC", text)
    text = _normalize_whitespace(text)
    text = _normalize_minus(text)
    text = _normalize_multiply(text)
    text = _normalize_fractions_ascii(text)
    text = _normalize_scientific_notation(text)
    return text


def normalize_output(text: str) -> str:
    """Aggressive normalization for output/evaluation targets."""
    if not text:
        return ""

    text = _normalize_scientific_notation(text)
    text = unicodedata.normalize("NFKC", text)
    text = _normalize_whitespace(text)
    text = _normalize_minus(text)
    text = _normalize_multiply(text)
    text = _normalize_fractions_ascii(text)
    text = _normalize_scientific_notation(text)
    text = _normalize_units(text)
    text = _normalize_equation_spacing(text)
    text = _fractions_to_decimal(text)
    return text


def extract_value_unit_explanation(text: str) -> Dict[str, Optional[str]]:
    """Extract a numeric value, unit, and explanation from a normalized output."""
    normalized = normalize_output(text)
    match = _NUMBER_PATTERN.search(normalized)
    if not match:
        return {"value": None, "unit": None, "explanation": normalized.strip() or None}

    value_text = match.group(0)
    value = _parse_number(value_text)
    rest = normalized[match.end() :].lstrip()

    unit_match = _UNIT_PATTERN.match(rest)
    unit = unit_match.group(0) if unit_match else None
    explanation = rest[unit_match.end() :].lstrip() if unit_match else rest

    return {
        "value": value,
        "unit": unit or None,
        "explanation": explanation or None,
    }


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\t ]+", " ", text)
    return text.strip()


def _normalize_minus(text: str) -> str:
    return re.sub(f"[{_MINUS_CHARS}]", "-", text)


def _normalize_multiply(text: str) -> str:
    return re.sub(f"[{_MULTIPLY_CHARS}]", "*", text)


def _normalize_fractions_ascii(text: str) -> str:
    text = text.replace("\u2044", "/")
    for frac, ascii_frac in _FRACTIONS_ASCII.items():
        text = text.replace(frac, ascii_frac)
    return text


def _normalize_scientific_notation(text: str) -> str:
    # Replace superscript powers like 10^(-3) written with superscripts.
    def repl(match: re.Match) -> str:
        base = match.group(1)
        exp = "".join(_SUPERSCRIPT_TO_ASCII[ch] for ch in match.group(2))
        return f"{base}^{exp}"

    text = re.sub(r"(\d)([\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b]+)", repl, text)
    return text


def _normalize_units(text: str) -> str:
    for token, replacement in _UNIT_NORMALIZATION.items():
        text = re.sub(rf"\b{re.escape(token)}\b", replacement, text, flags=re.IGNORECASE)
    return text


def _normalize_equation_spacing(text: str) -> str:
    text = re.sub(r"\s*([=/*+])\s*", r"\1", text)
    text = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", text)
    return text


def _fractions_to_decimal(text: str) -> str:
    for frac, dec in _FRACTIONS_DECIMAL.items():
        text = re.sub(rf"\b{re.escape(frac)}\b", dec, text)
    return text


_NUMBER_PATTERN = re.compile(
    r"[+-]?(?:\d+\.\d+|\d+)(?:e[+-]?\d+)?(?:\*10\^[+-]?\d+)?",
    flags=re.IGNORECASE,
)

_UNIT_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9/^\-]*")


def _parse_number(value_text: str) -> Optional[float]:
    value_text = value_text.replace(" ", "")
    sci_match = re.match(r"^(?P<coef>[+-]?(?:\d+\.\d+|\d+))\*10\^(?P<exp>[+-]?\d+)$", value_text)
    if sci_match:
        coef = float(sci_match.group("coef"))
        exp = int(sci_match.group("exp"))
        return coef * (10 ** exp)

    try:
        return float(value_text)
    except ValueError:
        return None
