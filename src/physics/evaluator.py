from __future__ import annotations

from typing import Optional

from src.eval.eval_physics import evaluate_physics_answer
from src.physics.types import PhysicsEval, PhysicsResult


class PhysicsEvaluator:
    def evaluate(self, result: PhysicsResult) -> PhysicsEval:
        if not result.task.correct:
            return PhysicsEval(result=result, is_correct=None, reason="missing_correct")
        if not result.model_answer:
            return PhysicsEval(result=result, is_correct=False, reason="missing_answer")

        is_correct = evaluate_physics_answer(result.model_answer, result.task.correct)
        reason = "match" if is_correct else "mismatch"
        return PhysicsEval(result=result, is_correct=is_correct, reason=reason)
