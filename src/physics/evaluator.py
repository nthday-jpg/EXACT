from __future__ import annotations

import math
from typing import Any, Optional

from src.eval.eval_physics import evaluate_physics_answer
from src.physics.types import PhysicsEval, PhysicsResult


class PhysicsEvaluator:
    def evaluate(self, result: PhysicsResult) -> PhysicsEval:
        if not result.task.correct:
            return PhysicsEval(result=result, is_correct=None, reason="missing_correct")
        if not result.model_answer:
            reason = _reason_from_error(result.error) or "missing_answer"
            return PhysicsEval(result=result, is_correct=False, reason=reason)

        reason = _reason_from_error(result.error) or _reason_from_nan(
            result.model_answer
        )
        if reason:
            return PhysicsEval(result=result, is_correct=False, reason=reason)

        try:
            is_correct = evaluate_physics_answer(
                result.task.question,
                result.model_answer,
                model_raw_output=result.raw_response,
                correct_answer=result.task.correct,
            )
        except Exception as exc:
            result.error = str(exc)
            return PhysicsEval(result=result, is_correct=False, reason="eval_error")

        reason = "match" if is_correct else "mismatch"
        return PhysicsEval(result=result, is_correct=is_correct, reason=reason)


def _reason_from_error(error: Optional[str]) -> Optional[str]:
    if not error:
        return None
    text = error.lower()
    if "json" in text and "decode" in text:
        return "json_parse_error"
    if "syntaxerror" in text or "invalid syntax" in text:
        return "code_syntax_error"
    if "nameerror" in text:
        return "code_name_error"
    return None


def _reason_from_nan(model_answer: dict) -> Optional[str]:
    ans = model_answer.get("ans")
    if ans is None:
        return None
    values = ans if isinstance(ans, list) else [ans]
    for value in values:
        numeric = _to_number(value)
        if numeric is not None and not math.isfinite(numeric):
            return "nan_answer"
    return None


def _to_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None
