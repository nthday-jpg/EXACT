## EXACT

Lightweight workspace for the EXACT educational QA challenge datasets and experiments.

## Repository Structure

- context.md: Challenge description, constraints, and submission requirements.
- main.py: Entry point for experiments or quick scripts.
- pyproject.toml: Python dependencies and tooling.
- data/logic_based.json: Logic-based dataset (Type 1) with NL premises, FOL, questions, and answers.
- data/physic.csv: Physics dataset (Type 2) with numeric problems.
- src/: Source code for logic, physics, LLM helpers, and evaluation.

## Source Structure

- src/logic/: Logic parsing, normalization, and rule-based reasoning utilities.
- src/physics/: Physics formula helpers and numeric solvers.
- src/llm/: LLM wrappers, prompts, and model utilities (open-source only).
- src/eval/: Scoring and evaluation utilities.

## NL to FOL Module

The module in [src/logic/nl_to_fol.py](src/logic/nl_to_fol.py) provides a baseline parser that:

- normalizes logic symbols to ASCII (e.g., `∀` -> `ForAll`, `→` -> `->`)
- detects simple conditional patterns like "If X, then Y"
- outputs a lightweight FOL-like string for quick inspection

Example usage:

```python
from src.logic.nl_to_fol import nl_to_fol

premises = [
	"If a student completes Course A, they can enroll in Course B.",
	"There exists a student who completed Course A.",
]

fol = nl_to_fol(premises)
for line in fol:
	print(line)
```

Notes:

- This is a baseline rule-based parser intended for fast iteration.
- For higher accuracy, replace it with a dedicated parser or an open-source NL-to-FOL model.
