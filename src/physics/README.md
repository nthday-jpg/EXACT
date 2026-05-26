# Physics Module

This folder provides a small, composable physics pipeline that can be used in sync, async, or batch mode and is ready for a future endpoint.

## Overview

- types.py: Data contracts for tasks, results, and evaluations.
- solver.py: LLM-based solver that builds a prompt, calls the model, and executes returned code.
- evaluator.py: Wraps the physics evaluator to mark answers as correct or incorrect.
- runner.py: Orchestrates sync, async, and batch execution. Supports optional self-correction.
- api.py: Endpoint-friendly entrypoint that wires everything together.

## Data Flow

PhysicsTask -> PhysicsSolver -> PhysicsResult -> PhysicsEvaluator -> PhysicsEval

## Self-Correct

Self-correction is optional. Implement the SelfCorrector protocol and pass it into PhysicsRunner.

## Example

from src.physics.api import run_physics
from src.physics.types import PhysicsTask


tasks = [
    PhysicsTask(
        question="A resonant RLC circuit has a resistance R = 25 ohm and an applied voltage U = 100 V. What is the power?",
        correct={"ans": "400", "unit": "W"},
    )
]

results = run_physics(
    tasks,
    model_name="Qwen/Qwen3-8B:featherless-ai",
    api_key="...",
    system_prompt="You are a physics expert. Return JSON with python_code that sets ans and unit.",
)

for r in results:
    print(r.is_correct, r.reason)
