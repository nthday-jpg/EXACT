from __future__ import annotations

import asyncio
from typing import Iterable, List, Optional

from tqdm import tqdm

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

    def run(self, tasks: Iterable[PhysicsTask], *, verbose: bool = False) -> List[PhysicsEval]:
        task_list = list(tasks)
        iterator = tqdm(task_list, desc="Physics", disable=not verbose)
        return [self._run_one(task) for task in iterator]

    async def run_async(
        self,
        tasks: Iterable[PhysicsTask],
        *,
        concurrency: int = 8,
        verbose: bool = False,
    ) -> List[PhysicsEval]:
        semaphore = asyncio.Semaphore(concurrency)
        task_list = list(tasks)
        results: List[Optional[PhysicsEval]] = [None] * len(task_list)

        async def _run_task(index: int, task: PhysicsTask) -> tuple[int, PhysicsEval]:
            async with semaphore:
                result = await asyncio.to_thread(self._run_one, task)
                return index, result

        pending = [_run_task(idx, task) for idx, task in enumerate(task_list)]
        progress = tqdm(total=len(task_list), desc="Physics", disable=not verbose)
        try:
            for coro in asyncio.as_completed(pending):
                index, result = await coro
                results[index] = result
                progress.update(1)
        finally:
            progress.close()

        return [result for result in results if result is not None]


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
