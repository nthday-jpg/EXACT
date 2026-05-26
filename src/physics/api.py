from __future__ import annotations

from typing import Iterable, List, Optional

from src.agents.self_correct.interface import SelfCorrector
from src.physics.evaluator import PhysicsEvaluator
from src.physics.runner import PhysicsRunner
from src.physics.solver import PhysicsSolver
from src.physics.types import PhysicsEval, PhysicsTask


def run_physics(
    tasks: Iterable[PhysicsTask],
    *,
    model_name: str,
    api_key: Optional[str],
    system_prompt: str,
    heuristic_prompt: Optional[str] = None,
    temperature: float = 0.1,
    extra_body: Optional[dict] = None,
    self_corrector: Optional[SelfCorrector] = None,
    max_attempts: int = 2,
) -> List[PhysicsEval]:
    solver = PhysicsSolver(
        model_name=model_name,
        api_key=api_key,
        system_prompt=system_prompt,
        heuristic_prompt=heuristic_prompt,
        temperature=temperature,
        extra_body=extra_body,
    )
    evaluator = PhysicsEvaluator()
    runner = PhysicsRunner(
        solver=solver,
        evaluator=evaluator,
        self_corrector=self_corrector,
        max_attempts=max_attempts,
    )
    return runner.run(tasks)
