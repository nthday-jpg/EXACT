"""Normalization utilities for the QA datasets."""

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


def normalize_logic_premise_text(text: str) -> str:
    """Normalize logic premises to avoid parser-hostile tokens."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2192", "->")
    text = text.replace("\u2194", "<->")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    def join_title(match: re.Match) -> str:
        parts = match.group(2).split()
        return f"{match.group(1)}{''.join(parts)}"

    text = re.sub(
        r"\b(Dr|Prof|Mr|Mrs|Ms)\.?\s+([A-Za-z][A-Za-z-]*(?:\s+[A-Za-z][A-Za-z-]*)*)",
        join_title,
        text,
    )
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*\u00b0C\b", r"\1C", text)

    def normalize_time(match: re.Match) -> str:
        hour = match.group(1)
        minute = match.group(2) or ""
        ampm = match.group(3).upper()
        return f"Time{hour}{minute}{ampm}"

    text = re.sub(r"\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b", normalize_time, text)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*hours?\b", r"Duration\1Hours", text)
    text = text.replace("'", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_logic_fol_entry(text: str) -> str:
    """Normalize FOL strings to align with the Z3 parser expectations."""
    if not text:
        return text

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\ufffd\s*forall\b", "forall", text, flags=re.IGNORECASE)
    text = re.sub(r"\ufffd\s*exists\b", "exists", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bforall\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*",
        r"ForAll(\1, ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bexists\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*",
        r"Exists(\1, ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bforall\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*",
        r"ForAll(\1, ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bexists\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*",
        r"Exists(\1, ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\u2200\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*", r"ForAll(\1, ", text)
    text = re.sub(r"\u2203\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*", r"Exists(\1, ", text)
    text = re.sub(r"\u2200\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*", r"ForAll(\1, ", text)
    text = re.sub(r"\u2203\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*", r"Exists(\1, ", text)
    text = re.sub(r"\u2200\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*", r"ForAll(\1, ", text)
    text = re.sub(r"\u2203\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*", r"Exists(\1, ", text)

    replacements = {
        "\u2192": "->",
        "\u2227": "AND",
        "\u2228": "OR",
        "\u00ac": "NOT ",
        "\u2194": "<->",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2260": "!=",
        "\u2208": "IN",
        "\u2295": "OR",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\bNOT\(", "NOT (", text)
    text = re.sub(r"\bimplies\b", "->", text, flags=re.IGNORECASE)
    text = text.replace("&", " AND ")
    text = text.replace("~", " NOT ")
    text = text.replace("^", " AND ")
    
    def normalize_args(match: re.Match) -> str:
        pred_name = match.group(1)
        args_str = match.group(2)
        args = [arg.strip() for arg in args_str.split(",")]
        normalized_args = [arg.replace(" ", "_").replace(".", "_") for arg in args]
        return f"{pred_name}({', '.join(normalized_args)})"

    text = re.sub(r"\b([A-Za-z_][A-Za-z0-9_-]*)\s*\(([^()]+)\)", normalize_args, text)
    
    # Standardize spaces around logical operators, comparisons, commas and parentheses
    text = re.sub(r"\s*<->\s*", " <-> ", text)
    text = re.sub(r"(?<!<)\s*->\s*", " -> ", text)
    text = re.sub(r"\s*\bAND\b\s*", " AND ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\bOR\b\s*", " OR ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\bNOT\b\s*", " NOT ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(>=|<=|!=)\s*", r" \1 ", text)
    text = re.sub(r"(?<![<>!=])\s*=\s*(?![=>])", " = ", text)
    text = re.sub(r"(?<![-<])\s*>\s*(?!=)", " > ", text)
    text = re.sub(r"\s*<\s*(?![-=])", " < ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    
    text = re.sub(r"\s+", " ", text)
    
    open_count = text.count("(")
    close_count = text.count(")")
    if close_count < open_count:
        text = text + ")" * (open_count - close_count)
    return text.strip()


def normalize_physics_input(text: str) -> str:
    """Conservative normalization for physics input prompts."""
    if not text:
        return ""

    text = _normalize_scientific_notation(text)
    text = unicodedata.normalize("NFKC", text)
    text = _normalize_whitespace(text)
    text = _normalize_minus(text)
    text = _normalize_multiply(text)
    text = _normalize_exponent_notation(text)
    text = _normalize_fractions_ascii(text)
    text = _normalize_scientific_notation(text)
    text = _normalize_exponent_notation(text)
    return text


def normalize_physics_output(text: str) -> str:
    """Aggressive normalization for physics output/evaluation targets."""
    if not text:
        return ""

    text = _normalize_scientific_notation(text)
    text = unicodedata.normalize("NFKC", text)
    text = _normalize_whitespace(text)
    text = _normalize_minus(text)
    text = _normalize_multiply(text)
    text = _normalize_exponent_notation(text)
    text = _normalize_fractions_ascii(text)
    text = _normalize_scientific_notation(text)
    text = _normalize_exponent_notation(text)
    text = _normalize_units(text)
    text = _normalize_equation_spacing(text)
    text = _fractions_to_decimal(text)
    return text


def extract_value_unit_explanation(text: str) -> Dict[str, Optional[str]]:
    """Extract a numeric value, unit, and explanation from a normalized output."""
    normalized = normalize_physics_output(text)
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
        exp = "".join(_SUPERSCRIPT_TO_ASCII[ch] for ch in match.group(1))
        return f"^{exp}"

    text = re.sub(
        r"([\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b]+)",
        repl,
        text,
    )
    return text


def _normalize_exponent_notation(text: str) -> str:
    # Convert 10^exponent expressions into e-notation.
    text = re.sub(
        r"(?<!\w)(\d+(?:\.\d+)?)(?:\s*[*xX]\s*)?10\^(?:\{)?([+-]?\d+)(?:\})?",
        r"\1e\2",
        text,
    )
    text = re.sub(r"\b10\^(?:\{)?([+-]?\d+)(?:\})?\b", r"1e\1", text)
    return text


def normalize_physics_scientific_text(text: str) -> str:
    """Normalize scientific notation for physics dataset strings."""
    if not text:
        return ""

    text = _normalize_scientific_notation(text)
    text = re.sub(r"\s*[\u00d7\u00b7]\s*", " * ", text)
    text = re.sub(r"(\d)\s*\.\s*(10\^)", r"\1 * \2", text)
    text = re.sub(r"(\d)\s*\*\s*(10\^)", r"\1 * \2", text)
    text = _normalize_exponent_notation(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


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
