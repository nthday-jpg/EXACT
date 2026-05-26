# Logical Reasoning System

The EXACT logic system provides a unified framework for executing formal logical reasoning on natural language text. It divides logical reasoning into two isolated, modular pipelines: **Translation** (converting NL to FOL) and **Reasoning** (validating entailment using Z3 and explaining proofs).

```
                  ┌──────────────────────┐
                  │ Natural Language     │
                  │ Premises & Conclusion│
                  └──────────┬───────────┘
                             │
                             ▼
               ┌──────────────────────────┐
               │ 1. Translation Pipeline  │ (src/logic/translation)
               │ (LLM-based FOL Compiler) │
               └──────────┬───────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ First-Order Logic    │
                  │ Formulas (FOL)       │
                  └──────────┬───────────┘
                             │
                             ▼
               ┌──────────────────────────┐
               │ 2. Reasoning Pipeline    │ (src/logic/reasoning)
               │ (Z3 SMT Solver & LLM)    │
               └──────────┬───────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Formal Verification  │
                  │ & NL Proof Explainer │
                  └──────────────────────┘
```

---

## Directory Layout

- **`translation/`**: Pipeline 1. Exposes `NLToFOLPipeline` to compile natural language statements into logical representations.
- **`reasoning/`**: Pipeline 2. Exposes `ReasoningPipeline` and `verify_with_z3` to verify logic expressions via the Z3 SMT solver and explain the outcomes (unsat core or counterexample) back in natural language.
- **`pipeline.py`**: A backward-compatible orchestrator class (`LogicalReasoningPipeline`) that stitches both pipelines together for end-to-end processing.
- **`z3_verifier.py`**: A backward-compatible forwarding interface for legacy scripts importing Z3 utilities.

---

## End-to-End Orchestrator

The top-level `LogicalReasoningPipeline` integrates both pipelines and exposes a single simple interface.

### Example Code

```python
from src.logic.pipeline import LogicalReasoningPipeline

# 1. Initialize the end-to-end pipeline (supporting local or remote models)
pipeline = LogicalReasoningPipeline(use_local=False, llm_client=your_llm_client)

# 2. Define natural language inputs
premises = [
    "Every human is mortal.",
    "Socrates is a human."
]
conclusion = "Socrates is mortal."

# 3. Run the end-to-end execution
result = pipeline.run_pipeline(premises, conclusion)

# 4. Inspect outputs
print("Parsed Formulas:")
print("Premises FOL:", result["premises_fol"])
print("Conclusion FOL:", result["conclusion_fol"])

verification = result["verification"]
if verification["result"].r == -1: # Z3 unsat means contradiction proven
    print("\nEntailment Status: 🟢 LOGICALLY CORRECT")
    print("Minimal Unsat Core:", verification["unsat_core"])
    print("\nGenerated Step-by-Step Reason Explanation:")
    print(result["reasoning"])
```
