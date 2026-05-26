from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd

from src.physics.evaluator import PhysicsEvaluator
from src.physics.runner import PhysicsRunner
from src.physics.solver import PhysicsSolver
from src.physics.types import PhysicsEval, PhysicsTask


def load_physics_tasks(csv_path: str, *, num_samples: int = -1, seed: int = 42) -> List[PhysicsTask]:
    df = pd.read_csv(csv_path)
    if num_samples != -1:
        num_samples = min(num_samples, len(df))
        df = df.sample(n=num_samples, random_state=seed)
    tasks: List[PhysicsTask] = []
    for _, row in df.iterrows():
        correct = {"ans": row["answer"], "unit": row["unit"]}
        task = PhysicsTask(question=row["question"], correct=correct)
        tasks.append(task)
    return tasks


def collect_failures(evals: List[PhysicsEval]) -> List[dict]:
    failures: List[dict] = []
    for evaluation in evals:
        if evaluation.is_correct is True:
            continue
        result = evaluation.result
        failures.append(
            {
                "question": result.task.question,
                "correct": result.task.correct,
                "model_answer": result.model_answer,
                "raw_response": result.raw_response,
                "error": result.error,
                "reason": evaluation.reason,
            }
        )
    return failures


def run_exploration(
    *,
    csv_path: str,
    output_path: str,
    model_name: str,
    api_key: Optional[str],
    system_prompt: str,
    heuristic_prompt: str,
    num_samples: int = -1,
    seed: int = 42,
    temperature: float = 0.1,
    extra_body: Optional[Dict[str, Any]] = None,
    verbose: bool = True,
) -> List[dict]:
    solver = PhysicsSolver(
        model_name=model_name,
        api_key=api_key,
        system_prompt=system_prompt,
        heuristic_prompt=heuristic_prompt,
        temperature=temperature,
        extra_body=extra_body or {"chat_template_kwargs": {"enable_thinking": False}},
    )
    evaluator = PhysicsEvaluator()
    runner = PhysicsRunner(solver=solver, evaluator=evaluator)

    tasks = load_physics_tasks(csv_path, num_samples=num_samples, seed=seed)
    evals = runner.run(tasks, verbose=verbose)
    failures = collect_failures(evals)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(failures, f, indent=4)

    return failures
