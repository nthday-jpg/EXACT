from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Dict, List

from src.physics.types import PhysicsTask


def _normalize_correct(record: Dict[str, Any]) -> Dict[str, Any]:
    correct = record.get("correct_answer")
    if isinstance(correct, dict):
        answer = correct.get("ans", correct.get("answer"))
        unit = correct.get("unit", record.get("correct_units"))
    else:
        answer = correct
        unit = record.get("correct_units")
    if unit is None and isinstance(record.get("unit"), str):
        unit = record.get("unit")
    return {"ans": answer, "unit": unit}


def _load_tasks_from_csv(path: Path) -> List[PhysicsTask]:
    tasks: List[PhysicsTask] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            question = row.get("question")
            if question is None:
                raise ValueError(f"Missing question field in {path}")
            correct = {"ans": row.get("answer"), "unit": row.get("unit")}
            tasks.append(PhysicsTask(question=question, correct=correct))
    return tasks


def _load_tasks_from_json(path: Path) -> List[PhysicsTask]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        records = json.loads(text)
    if not isinstance(records, list):
        raise ValueError(f"Expected a list of task records in {path}")

    tasks: List[PhysicsTask] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"Expected each record in {path} to be an object")
        question = record.get("question")
        if question is None:
            raise ValueError(f"Missing question field in {path}")
        correct = _normalize_correct(record)
        tasks.append(PhysicsTask(question=question, correct=correct))
    return tasks


def load_physics_tasks(input_path: str, *, num_samples: int = -1, seed: int = 42) -> List[PhysicsTask]:
    path = Path(input_path)
    if path.suffix.lower() in {".json", ".jsonl"}:
        tasks = _load_tasks_from_json(path)
    elif path.suffix.lower() == ".csv":
        tasks = _load_tasks_from_csv(path)
    else:
        raise ValueError(f"Unsupported input format: {path.suffix}")

    if num_samples != -1:
        num_samples = min(num_samples, len(tasks))
        rng = random.Random(seed)
        tasks = rng.sample(tasks, num_samples)

    return tasks