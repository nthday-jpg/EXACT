from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from tqdm import tqdm
import asyncio

from src.physics.api import run_physics
from src.physics.evaluator import PhysicsEvaluator
from src.physics.types import PhysicsEval, PhysicsResult, PhysicsTask
from src.utils.physics_tasks import load_physics_tasks


def collect_failures(evals: List[PhysicsEval]) -> List[dict]:
    failures: List[dict] = []
    for evaluation in evals:
        if evaluation.is_correct is True:
            continue
        result = evaluation.result
        tokens = result.tokens or {}
        failures.append(
            {
                "question": result.task.question,
                "correct": result.task.correct,
                "model_answer": result.model_answer,
                "raw_response": result.raw_response,
                "error": result.error,
                "reason": evaluation.reason,
                "input_tokens": tokens.get("input_tokens"),
                "output_tokens": tokens.get("output_tokens"),
            }
        )
    return failures


async def run_exploration(
    *,
    csv_path: str,
    output_path: str,
    model_name: str,
    api_key: Optional[str],
    router_model_name: Optional[str] = None,
    num_samples: int = -1,
    seed: int = 42,
    temperature: float = 0.1,
    enable_thinking: bool = False,
    concurrency: int = 8,
) -> List[dict]:
    tasks = load_physics_tasks(csv_path, num_samples=num_samples, seed=seed)
    evals: List[PhysicsEval] = []
    semaphore = asyncio.Semaphore(concurrency)
    evaluator = PhysicsEvaluator()

    async def _run_task(task: PhysicsTask) -> PhysicsEval:
        async with semaphore:
            try:
                return await run_physics(
                    task,
                    model_name=model_name,
                    api_key=api_key,
                    router_model_name=router_model_name,
                    evaluator=evaluator,
                    temperature=temperature,
                    enable_thinking=enable_thinking,
                )
            except Exception as exc:
                result = PhysicsResult(
                    task=task,
                    model_answer=None,
                    raw_response="",
                    error=str(exc),
                    tokens=None,
                        elapsed_s=0.0,
                        domains=None,
                )
                return PhysicsEval(result=result, is_correct=False, reason="exception")

    pending = [_run_task(task) for task in tasks]
    progress = tqdm(total=len(tasks), desc="Physics")
    try:
        for coro in asyncio.as_completed(pending):
            evaluation = await coro
            evals.append(evaluation)
            progress.update(1)
    finally:
        progress.close()
    failures = collect_failures(evals)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(failures, f, indent=4)

    return failures
