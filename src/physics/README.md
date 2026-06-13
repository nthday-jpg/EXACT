# Physics Module

This folder provides a router-based physics pipeline that assembles domain reasoning policies on the fly and executes a solver with strict output constraints.

## Overview

- api.py: Entry point for routed execution. Performs text preprocessing, loads solver instructions, and routes the execution.
- router.py: LLM classifier for domains + question type.
- registry.py: Reasoning Policies assembly (global ontology + domain reasoning policies + few-shots).
- solver.py: LLM-based solver that builds a prompt and executes returned code.
- evaluator.py: Marks answers as correct/incorrect.
- runner.py: Orchestrates execution with optional self-correction.
- types.py: Data contracts for tasks, results, evaluations.
- preprocessing.py: Preprocesses text and standardizes unit magnitudes to SI base units.
- postprocessing.py: Converts answers back to standard engineering units with appropriate prefixes.
- llm_execution.py: Executes LLM-generated code safely in a sandbox using SymPy.

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
├── preprocessing.py
├── postprocessing.py
├── llm_execution.py
├── instructions/
│   ├── router.md      # router config (domains, question types)
│   └── solver.md      # solver constraints & output format
├── reasoning_policies/ # domain reasoning policies
├── fewshot/            # few-shot examples by domain
└── global_ontology/    # optional global ontology (global.md)
```

## Routed Pipeline

```
Question
  -> preprocess()
  -> classify_question()
  -> registry.get_solver_prompt(classification)
  -> solver.solve(task)
  -> evaluator.evaluate(result)
  -> PhysicsEval
```

## Reasoning Policies Assembly Format

The registry assembles prompts in this order:

```
<global_ontology>
... optional global concepts ...
</global_ontology>

<domain_reasoning policies>
... domain reasoning policies ...
</domain_reasoning policies>

<fewshots>
... few-shot examples ...
</fewshots>
```

## Example

```python
import asyncio
from src.physics.api import run_physics
from src.physics.types import PhysicsTask

async def main():
    task = PhysicsTask(
        question="A resonant RLC circuit has a resistance R = 25 ohm and an applied voltage U = 100 V. What is the power?",
        correct={"ans": "400", "unit": "W"},
    )

    evaluation = await run_physics(
        task,
        model_name="Qwen/Qwen3-8B:featherless-ai",
        api_key="your_hugging_face_token",
    )

    print(f"Is Correct: {evaluation.is_correct}")
    print(f"Reason: {evaluation.reason}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Self-Correction

Self-correction is supported inside `run_physics`. You can pass a `self_corrector` parameter (which implements the `SelfCorrector` protocol) to `run_physics` to handle code execution errors and auto-correction.

## Example Script / Tests

See [smoke_test_api.py](file:///d:/mduy/source/repos/EXACT/tests/smoke_test_api.py) for an integration test showing the end-to-end FastAPI prediction server deployment and pipeline testing.
