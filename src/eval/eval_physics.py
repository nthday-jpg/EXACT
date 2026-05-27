"""Evaluation helpers for physics dataset answers."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

import sympy as sp

import pint

from src.physics.postprocessing import postprocess_answer



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

_UNIT_EQUIV = {
	"v/m": "v/m",
	"n/c": "v/m",
}


@dataclass(frozen=True)
class _Item:
	value: Any
	unit: str


def evaluate_physics_answer(model: dict, correct: dict) -> bool:
	"""Return True if model answer matches the correct answer.

	Both inputs must be dicts with keys:
	- ans: a value or list of values
	- unit: a unit string or list of unit strings
	"""
	if not isinstance(model, dict) or not isinstance(correct, dict):
		raise TypeError("model and correct must be dicts")

	model = postprocess_answer(model)
	correct = postprocess_answer(correct)

	model_items = _normalize_items(model)
	correct_items = _normalize_items(correct)

	if len(model_items) != len(correct_items):
		return False

	return _compare_item_sets(model_items, correct_items)


def _normalize_items(payload: dict) -> List[_Item]:
	ans = payload.get("ans")
	unit = payload.get("unit") or ""

	if isinstance(ans, list):
		ans_list = ans
	else:
		ans_list = [ans]

	if isinstance(unit, list):
		unit_list = unit
	else:
		unit_list = [unit] * len(ans_list)

	if len(unit_list) != len(ans_list):
		raise ValueError("ans and unit must have the same length")

	return [_Item(value=a, unit=_normalize_unit(str(u or ""))) for a, u in zip(ans_list, unit_list)]


def _compare_item_sets(model_items: List[_Item], correct_items: List[_Item]) -> bool:
	remaining = model_items[:]
	for correct_item in correct_items:
		match_idx = _find_match_index(remaining, correct_item)
		if match_idx is None:
			return False
		remaining.pop(match_idx)
	return True


def _find_match_index(candidates: List[_Item], target: _Item) -> Optional[int]:
	for idx, candidate in enumerate(candidates):
		if _items_match(candidate, target):
			return idx
	return None


def _items_match(model_item: _Item, correct_item: _Item) -> bool:
	model_val, model_unit = _coerce_value(model_item.value, model_item.unit)
	correct_val, correct_unit = _coerce_value(correct_item.value, correct_item.unit)

	if _is_numeric(model_val) and _is_numeric(correct_val):
		return _numeric_match(float(model_val), model_unit, float(correct_val), correct_unit)

	model_expr = _maybe_sympy_expr(model_val)
	correct_expr = _maybe_sympy_expr(correct_val)
	if model_expr is not None and correct_expr is not None:
		return _formula_match(model_expr, correct_expr)

	return _llm_or_text_match(str(model_val), str(correct_val))


def _coerce_value(value: Any, unit: str) -> Tuple[Any, str]:
	numeric = _to_number(value)
	if numeric is None:
		return value, _normalize_unit(unit)
	scaled_val, scaled_unit = _convert_to_si(numeric, unit)
	return scaled_val, scaled_unit


def _to_number(value: Any) -> Optional[float]:
	if isinstance(value, (int, float)):
		return float(value)
	if value is None:
		return None
	try:
		evaluated = sp.N(value)
		if evaluated.is_number:
			return float(evaluated)
	except (TypeError, ValueError):
		pass
	try:
		return float(str(value).strip())
	except (TypeError, ValueError):
		return None


def _convert_to_si(value: float, unit: str) -> Tuple[float, str]:
	unit = _normalize_unit(unit)
	if not unit:
		return value, unit

	ureg = pint.UnitRegistry()
	try:
		quantity = value * ureg(unit)
		quantity = quantity.to_base_units()
		return float(quantity.magnitude), str(quantity.units)
	except Exception:
		pass

	match = re.match(r"^([A-Za-z])(.*)$", unit)
	if not match:
		return value, unit

	prefix, rest = match.group(1), match.group(2)
	if prefix in _PREFIX_FACTORS and rest:
		return value * _PREFIX_FACTORS[prefix], rest

	return value, unit


def _is_numeric(value: Any) -> bool:
	return isinstance(value, (int, float)) and math.isfinite(value)


def _numeric_match(model_val: float, model_unit: str, correct_val: float, correct_unit: str) -> bool:
	if not _units_equivalent(model_unit, correct_unit):
		return False

	if math.isclose(correct_val, 0.0, abs_tol=1e-12):
		return math.isclose(model_val, 0.0, abs_tol=1e-12)

	rel_err = abs(model_val - correct_val) / abs(correct_val)
	return rel_err <= 0.01


def _normalize_unit(unit: str) -> str:
	unit = unit.strip()
	if unit == "-":
		return ""
	unit = unit.replace(" ", "")
	unit_lower = unit.lower()
	return _UNIT_EQUIV.get(unit_lower, unit_lower)


def _units_equivalent(left: str, right: str) -> bool:
	left_norm = _normalize_unit(left)
	right_norm = _normalize_unit(right)
	if left_norm == right_norm:
		return True
	if not left_norm and not right_norm:
		return True
	if left_norm and right_norm:
		try:
			ureg = pint.UnitRegistry()
			left_units = (1 * ureg(left_norm)).to_base_units().units
			right_units = (1 * ureg(right_norm)).to_base_units().units
			return left_units == right_units
		except Exception:
			return False
	return False


def _maybe_sympy_expr(value: Any) -> Optional[sp.Expr]:
	if isinstance(value, sp.Expr):
		return value
	if not isinstance(value, str):
		return None
	try:
		expr = sp.sympify(value)
	except (sp.SympifyError, TypeError, ValueError):
		return None
	if expr.free_symbols:
		return expr
	return None


def _formula_match(model_expr: sp.Expr, correct_expr: sp.Expr) -> bool:
	try:
		diff = sp.simplify(model_expr - correct_expr) #type: ignore
		return diff == 0
	except Exception:
		return False


def _llm_or_text_match(model_text: str, correct_text: str) -> bool:
	model_text = model_text.strip()
	correct_text = correct_text.strip()

	if not model_text or not correct_text:
		return False

	default_model = os.getenv("DEFAULT_MODEL")
	llm_model = os.getenv("PHYSICS_EVAL_LLM") or default_model
	if not llm_model:
		return _normalize_text(model_text) == _normalize_text(correct_text)

	try:
		from src.llm.llm_client import LLMClient

		api_key = os.getenv("PHYSICS_EVAL_LLM_KEY", "")
		system_prompt = (
			"You are a strict evaluator. Reply ONLY with 'yes' or 'no'. "
			"Decide if the model answer is semantically equivalent to the correct answer."
		)
		client = LLMClient(model_name=llm_model, api_key=api_key, system_prompt=system_prompt)
		response = client.generate(
			f"Correct answer: {correct_text}\nModel answer: {model_text}\nEquivalent?"
		)
		return str(response).strip().lower().startswith("y")
	except Exception:
		return _normalize_text(model_text) == _normalize_text(correct_text)


def _normalize_text(text: str) -> str:
	text = text.lower()
	text = re.sub(r"\s+", " ", text)
	return text.strip()
