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
- **`src/llm/prompts.py`**: Centralized configuration file storing all LLM system prompts and user prompt templates. Isolates prompt engineering from code execution for easy adjustment.
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

### 1. Answer Extraction & MCQ Process of Elimination
`run_pipeline()` always returns an explicit `answer` field:
- MCQ → the letter key of the best option (e.g. `"B"`). If no option is logically entailed (`unsat`), a consistency check is run. Direct contradictions (solver returns `unsat` when adding the option itself, i.e., `negate_conclusion=False`) are eliminated. The first consistent option is selected (Process of Elimination).
- Yes/No → `"Yes"` if entailed, `"No"` if negation entailed, `"Uncertain"` if Z3 cannot decide.

### 2. Confidence Score (`_compute_confidence`)
Derived from the Z3 verification result:

| Z3 result | Score range | Rationale |
|-----------|-------------|-----------|
| `unsat`, tight core | 0.75 – 1.00 | Formal proof with minimal premises |
| `sat` | 0.60 | Consistent candidate (MCQ Process of Elimination or statement fallback) |
| `unknown` | 0.30 | Solver undecided |

### 3. FOL Automatic Normalization & Repair Loop
After extraction, all FOL formulas are normalized using `normalize_logic_fol_entry()` to instantly resolve common syntax/casing issues (like `forall` vs `ForAll`, missing spaces, or unicode operators) without calling the LLM. Any remaining parsing errors are validated with `try_parse_fol()` and repaired via LLM (up to 2 retries).

### 4. Glossary-Constrained Translation (Two-Stage Compilation)
To prevent naming mismatches across premises (e.g. `well_structured` vs `wellStructured`), the compiler uses a two-stage translation:
1. **Stage 1 (Glossary Generation)**: Generates a unified JSON Glossary defining all unique predicates and constants.
2. **Stage 2 (Constrained Translation)**: Translates all statements strictly constrained by this Glossary.

### 5. Arithmetic & Temporal Logic Parsing
Mismatches in numeric sorts are resolved by pre-scanning formulas to identify numeric predicates and constants, automatically upgrading them to `IntSort()` in Z3. It supports temporal constants (e.g., `Time830AM` -> `IntVal(510)`) and durations (e.g., `Duration4Hours` -> `IntVal(240)`), as well as native arithmetic parsing rules for addition (`+`) and subtraction (`-`).

### 6. Neurosymbolic Proof-Guided CoT
When a proof is successful (`unsat`), the pipeline post-order traverses Z3's formal proof tree (`solver.proof()`), extracting asserted premises and logical deduction steps (like `mp` or `unit-resolution`) into a clean, structured proof skeleton. This mathematical skeleton is injected into the LLM prompt to guide CoT explanation generation, eliminating hallucinations and ensuring 100% mathematical grounding.

### Human-Like Explanations
Both `generate_reasoning()` and `generate_cot()` use prompts that explicitly prohibit verbatim premise copying and require the LLM to synthesize a flowing argument using transitional language (`Since`, `Therefore`, `As a result`, etc.).
