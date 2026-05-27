# Physics Module

This folder provides a router-based physics pipeline that assembles domain heuristics on the fly and executes a solver with strict output constraints.

## Overview

- api.py: Entry point for routed execution. Loads solver instructions internally.
- router.py: LLM classifier for domains + question type.
- registry.py: Heuristic assembly (global ontology + domain heuristics + few-shots).
- solver.py: LLM-based solver that builds a prompt and executes returned code.
- evaluator.py: Marks answers as correct/incorrect.
- runner.py: Orchestrates execution with optional self-correction.
- types.py: Data contracts for tasks, results, evaluations.

## Folder Layout

```
src/physics/
├── api.py
├── router.py
├── registry.py
├── solver.py
├── evaluator.py
├── runner.py
├── types.py
├── instructions/
│   ├── router.md      # router config (domains, question types)
│   └── solver.md      # solver constraints & output format
├── reasoning_policies/ # domain heuristics
├── fewshot/            # few-shot examples by domain
└── global_ontology/    # optional global ontology (global.md)
```

## Routed Pipeline

```
Question
  -> classify_question()
  -> registry.get_heuristic_prompt(classification)
  -> solver.solve(task)
  -> evaluator.evaluate(result)
  -> PhysicsEval
```

## Heuristic Assembly Format

The registry assembles prompts in this order:

```
<global_ontology>
... optional global concepts ...
</global_ontology>

<domain_heuristics>
... domain reasoning policies ...
</domain_heuristics>

<fewshots>
... few-shot examples ...
</fewshots>
```

## Example

```python
from src.physics.api import run_physics_with_router
from src.physics.types import PhysicsTask

tasks = [
    PhysicsTask(
        question="A resonant RLC circuit has a resistance R = 25 ohm and an applied voltage U = 100 V. What is the power?",
        correct={"ans": "400", "unit": "W"},
    )
]

results = run_physics_with_router(
    tasks,
    model_name="Qwen/Qwen3-8B:featherless-ai",
    api_key="...",
)

for r in results:
    print(r.is_correct, r.reason)
```

## Self-Correct

Self-correction is optional. Implement the SelfCorrector protocol and pass it into run_physics_with_router.

## Example Script

See scripts/example_router_pipeline.py for a full pipeline walkthrough.
