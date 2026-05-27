from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from src.physics.evaluator import PhysicsEvaluator
from src.physics.registry import get_heuristic_prompt
from src.physics.router import QuestionClassification, classify_question
from src.physics.runner import PhysicsRunner
from src.physics.solver import PhysicsSolver
from src.physics.types import PhysicsEval, PhysicsTask

if TYPE_CHECKING:
    from src.agents.self_correct.interface import SelfCorrector


async def run_physics(
    task: PhysicsTask,
    *,
    model_name: str,
    api_key: Optional[str],
    router_model_name: Optional[str] = None,
    evaluator: Optional[PhysicsEvaluator] = None,
    output_path: Optional[str] = None,
    temperature: float = 0.1,
    extra_body: Optional[dict] = None,
    self_corrector: Optional[SelfCorrector] = None,
    max_attempts: int = 2,
) -> PhysicsEval:
    """
    Run a single physics task with LLM-based routing and heuristic assembly.

    1. Route question to domains + question_type using LLM router
    2. Assemble heuristics (reasoning policies + few-shots) from registry
    3. Solve with assembled heuristic prompt
    4. Evaluate result
    """
    router_model = router_model_name or model_name
    system_prompt = _load_solver_instructions()

    try:
        classification = await asyncio.to_thread(
            classify_question,
            task.question,
            model_name=router_model,
            api_key=api_key,
            temperature=0.0,
        )
    except Exception:
        classification = QuestionClassification(["electrostatics", "geometry"], "Numerical")

    heuristic_prompt = get_heuristic_prompt(classification)

    solver = PhysicsSolver(
        model_name=model_name,
        api_key=api_key,
        system_prompt=system_prompt,
        heuristic_prompt=heuristic_prompt,
        temperature=temperature,
        extra_body=extra_body,
    )
    runner = PhysicsRunner(
        solver=solver,
        evaluator=evaluator,
        self_corrector=self_corrector,
        max_attempts=max_attempts,
    )
    evaluations = await asyncio.to_thread(runner.run, [task], verbose=False)
    evaluation = evaluations[0]

    if output_path:
        record = {
            "question": evaluation.result.task.question,
            "correct": evaluation.result.task.correct,
            "domains": classification.domains,
            "question_type": classification.question_type,
            "model_answer": evaluation.result.model_answer,
            "raw_response": evaluation.result.raw_response,
            "error": evaluation.result.error,
            "is_correct": evaluation.is_correct,
            "reason": evaluation.reason,
            "tokens": evaluation.result.tokens,
            "elapsed_s": evaluation.result.elapsed_s,
        }
        Path(output_path).write_text(json.dumps([record], indent=2), encoding="utf-8")

    return evaluation


def _load_solver_instructions() -> str:
    """Load solver instructions from instructions/solver.md."""
    solver_path = Path(__file__).parent / "instructions" / "solver.md"
    if solver_path.exists():
        return solver_path.read_text(encoding="utf-8")
    return ""
