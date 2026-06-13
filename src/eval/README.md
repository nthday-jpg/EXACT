# UGPhysics Evaluation Module (`eval_physics.py`)

This module implements a robust, multi-tiered evaluation pipeline tailored for grading undergraduate-level physics datasets. It is structurally aligned with the principles of the **MARJ (Model-Assistant Rule-based Judgment)** framework proposed in the *UGPhysics* paper, addressing cascading sources of grading error including floating-point rounding mismatches, dimensional unit scaling, mathematical expression simplifications, and conceptual text prose.

---

## 🚀 Core Features

- **Dynamic Significant Figure Matching**: Extracted directly from the ground truth answer strings to prevent structural floating-point discrepancies from causing false negatives.
- **Dimensional Unit Unification via Pint**: Automatically handles unit aliases, prefixes, and basic dimensional analysis (e.g., matching $V/m$ to $N/C$) by mapping measurements to irreducible SI base units.
- **SymPy Symbolic Validation**: Compiles mathematical formulas and expressions, ensuring algebraic equivalence regardless of variable positioning or the inclusion of constants (e.g., evaluating expressions with $\pi$ or trigonometric functions).
- **Model-Assisted Semantic Fallback**: Leverages an LLM gateway when evaluating conceptual prose or circuit-localized field descriptions where exact string mapping is impossible.

---

## 🧠 The MARJ Alignment

Standard mathematical evaluation scripts drop grading accuracy dramatically when handling physics datasets due to variations in how physical systems are described. This module mirrors the **MARJ** architecture:

1. **Rule-Based Judgment (R & J)**: It executes programmatic parsing of numerical limits and unit bounds first. Instead of using arbitrary relative thresholds, it evaluates structural properties dynamically by reading the experimental precision (significant figures) of the target truth.
2. **Model-Assistant (M)**: If numerical or algebraic paradigms fail, the problem domain is passed to a targeted semantic evaluator, preventing the classic penalty given to students who provide correct physical intuition using localized terminology or shorthand notation.

---

## 🗺️ Architecture & Evaluation Flow

The execution pathway for `evaluate_physics_answer(...)` runs through a fallback cascade:

1. **Data Normalization**: Structures raw inputs into rigid `_Item` domain data structures while retaining the layout format of the raw string input.
2. **Numerical Evaluation Logic**: If both answers are numeric, it attempts significant-figure alignment based on the correct answer template. If that fails, it falls back to a tight 2% relative error envelope.
3. **Symbolic Algebra Checking**: If the inputs contain variable mappings, SymPy extracts the symbols and computes whether the mathematical difference simplifies directly to `0`.
4. **Textual / Conceptual Validation**: If string structural mappings fail, an LLM evaluating agent verifies if the semantic intent matches specifically inside Electromagnetism, AC, or LC circuit domains.

---

### 1. `evaluate_physics_answer(question: str, model_answer: Any, model_raw_output: Optional[str], correct_answer: Any, *, llm_model: Optional[str] = None) -> bool`
The entry point for the physics evaluator. It compares the `model_answer` against the `correct_answer` using a fallback cascade of rule-based logic (significant figures, Pint dimensional checks, SymPy symbolic equivalence) and model-assisted semantic fallback.

Parameters:
- `question`: The text of the physics question.
- `model_answer`: The parsed answer dictionary or list from the solver (typically containing `ans` and `unit` keys).
- `model_raw_output`: The raw text response from the model, used as a context fallback if parsing fails.
- `correct_answer`: The ground truth answer dictionary or list containing `ans` and `unit` keys.
- `llm_model`: Optional model name to override the default LLM (e.g. Gemini) used for the semantic fallback check.

### 2. `_get_sig_figs(val_str: str) -> int` & `_round_to_sig_figs(...)`
Extracts precision context directly from the format of the correct answer string. For example:
- `8.2e3` $\rightarrow$ Extracts **2** significant figures.
- `8.156e3` $\rightarrow$ Evaluated against the target precision boundary by rounding down to `8.2e3`, triggering a valid match.

### 3. `_convert_to_si(value: float, unit: str)`
Utilizes a globally initialized `pint.UnitRegistry()` to avoid memory/object-clashing errors during run-time. Safely reduces metric metrics to standardized base-SI spaces.

### 4. `_maybe_sympy_expr(value: Any)`
Safely casts raw strings to symbolic representation while aggressively ignoring unstructured text prose that could trick simple `sympify` parsing blocks.