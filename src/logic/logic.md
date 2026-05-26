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
               │ + FOL Repair Loop        │
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
               │  ├─ Premise Filter       │
               │  ├─ Z3 SMT Solver        │
               │  └─ CoT Explainer (LLM)  │
               └──────────┬───────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  answer · confidence │
                  │  reasoning · cot     │
                  │  premises_fol · FOL  │
                  └──────────────────────┘
```

---

## Directory Layout

- **`translation/`**: Pipeline 1. Exposes `NLToFOLPipeline` to compile natural language statements into logical representations, with an automatic FOL Repair Loop.
- **`reasoning/`**: Pipeline 2. Exposes `ReasoningPipeline` with premise relevance filtering, Z3 SMT verification, and human-like CoT explanation generation.
- **`pipeline.py`**: A backward-compatible orchestrator class (`LogicalReasoningPipeline`) that stitches both pipelines together for end-to-end processing.
- **`z3_verifier.py`**: A backward-compatible forwarding interface for legacy scripts importing Z3 utilities.

---

## End-to-End Orchestrator

The top-level `LogicalReasoningPipeline` integrates both pipelines and exposes a single simple interface.

### Output Fields

`run_pipeline()` returns a dictionary with the following fields:

| Field | Type | Description |
|---|---|---|
| `answer` | `str` | Extracted answer: letter key for MCQ (`"B"`), `"Yes"` / `"No"` / `"Uncertain"` for statement queries |
| `confidence` | `float` | Confidence score in `[0.30, 1.00]` derived from Z3 result and unsat core tightness |
| `reasoning` | `str` | Human-like natural language explanation (flowing argument, not premise recitation) |
| `cot` | `list[str]` | Structured Chain-of-Thought steps parsed from `reasoning` (e.g. `["Step 1: ...", "Step 2: ..."]`) |
| `premises_fol` | `list[str]` | FOL formulas for the (filtered) premises passed to Z3 |
| `conclusion_fol` | `str` | FOL formula for the conclusion / chosen option |
| `verification` | `dict` | Raw Z3 result: `result`, `proof`, `unsat_core`, `model` |

### Example Code

```python
from src.logic.pipeline import LogicalReasoningPipeline

# 1. Initialize the end-to-end pipeline
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
print("Answer:", result["answer"])           # "Yes"
print("Confidence:", result["confidence"])   # e.g. 1.0
print("Explanation:", result["reasoning"])
print("CoT steps:", result["cot"])
# ["Step 1: Since every human is mortal and Socrates is human...",
#  "Step 2: Therefore Socrates must be mortal."]
```

### MCQ Example

```python
conclusion_mcq = (
    "Based on the premises, what can we conclude?\n"
    "A. The curriculum lacks engagement\n"
    "B. The curriculum enhances critical thinking\n"
    "C. No conclusion can be drawn\n"
    "D. The faculty is ineffective"
)

result = pipeline.run_pipeline(premises, conclusion_mcq)
print(result["answer"])      # "B"
print(result["confidence"])  # e.g. 0.917
print(result["cot"])         # ["Step 1: ...", "Step 2: ...", ...]
```

---

## Pipeline Extensions

The following improvements have been applied on top of the baseline:

### 1. Answer Extraction
`run_pipeline()` always returns an explicit `answer` field:
- MCQ → the letter key of the best option (e.g. `"B"`)
- Yes/No → `"Yes"` if entailed, `"No"` if negation entailed, `"Uncertain"` if Z3 cannot decide

### 2. Confidence Score (`_compute_confidence`)
Derived from the Z3 verification result:

| Z3 result | Score range | Rationale |
|-----------|-------------|-----------|
| `unsat`, tight core | 0.90 – 1.00 | Formal proof with minimal premises |
| `unsat`, large core | 0.75 – 0.90 | Formal proof, less focused |
| `sat` | 0.60 | Counterexample found |
| `unknown` | 0.30 | Solver undecided |

### 3. MCQ Full Scan
All options are verified independently; the one with the **smallest unsat core** (tightest proof) wins. Falls back to the first option if none yield `unsat`.

### 4. FOL Repair Loop (`_validate_and_repair`)
After translation, each FOL formula is validated with `try_parse_fol()`. Broken formulas are sent back to the LLM with the exact parse error for repair (up to 2 retries).

### 5. Premise Relevance Filtering (`filter_relevant_premises`)
When there are more than 3 premises, the LLM selects the top-k most relevant to the conclusion before Z3 verification. Falls back to all premises if filtering fails or fewer than 2 survive.

### 6. Structured CoT Output (`generate_cot`)
`generate_cot()` instructs the LLM to produce numbered steps (`Step N: ...`) and parses them into a list. The `reasoning` (raw string) is retained for backward compatibility alongside the new `cot` list.

### Human-Like Explanations
Both `generate_reasoning()` and `generate_cot()` use prompts that explicitly prohibit verbatim premise copying and require the LLM to synthesize a flowing argument using transitional language (`Since`, `Therefore`, `As a result`, etc.).
