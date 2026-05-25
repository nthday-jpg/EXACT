from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, List, Optional

from src.agents.self_correct.interface import SelfCorrector
from src.physics.evaluator import PhysicsEvaluator
from src.physics.solver import PhysicsSolver
from src.physics.types import PhysicsEval, PhysicsResult, PhysicsTask


class PhysicsRunner:
    def __init__(
        self,
        *,
        solver: PhysicsSolver,
        evaluator: PhysicsEvaluator,
        self_corrector: Optional[SelfCorrector] = None,
        max_attempts: int = 2,
    ) -> None:
        self._solver = solver
        self._evaluator = evaluator
        self._self_corrector = self_corrector
        self._max_attempts = max(1, max_attempts)

    def run(self, tasks: Iterable[PhysicsTask]) -> List[PhysicsEval]:
        return [self._run_one(task) for task in tasks]

    async def run_async(self, tasks: Iterable[PhysicsTask], concurrency: int = 8) -> List[PhysicsEval]:
        semaphore = asyncio.Semaphore(concurrency)

        async def _run_task(task: PhysicsTask) -> PhysicsEval:
            async with semaphore:
                return await asyncio.to_thread(self._run_one, task)

        return await asyncio.gather(*[_run_task(task) for task in tasks])


    def _run_one(self, task: PhysicsTask) -> PhysicsEval:
        attempt = 0
        current_task = task
        last_result: Optional[PhysicsResult] = None

        while attempt < self._max_attempts:
            attempt += 1
            result = self._solver.solve(current_task)
            last_result = result
            evaluation = self._evaluator.evaluate(result)

            if evaluation.is_correct is True or not self._self_corrector:
                return evaluation

            proposed = self._self_corrector.propose_fix(result)
            if not proposed:
                return evaluation

            current_task = proposed

        if last_result is None:
            last_result = self._solver.solve(task)
        return self._evaluator.evaluate(last_result)
