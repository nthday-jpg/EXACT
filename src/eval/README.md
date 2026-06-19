# Physics Evaluation Module (`eval_physics.py`)

This module implements a robust, multi-tiered evaluation pipeline for grading undergraduate-level physics problems. It is structurally aligned with the **MARJ (Model-Assistant Rule-based Judgment)** framework, addressing cascading sources of grading error including floating-point rounding mismatches, dimensional unit scaling, mathematical expression simplifications, and conceptual text prose.

---

## 🚀 Core Features

- **Dynamic Significant Figure Matching**: Extracts precision directly from ground truth answer strings to prevent structural floating-point discrepancies from causing false negatives.
- **Dimensional Unit Unification via Pint**: Automatically handles unit aliases, metric prefixes, and dimensional analysis (e.g., matching `V/m` to `N/C`) by mapping measurements to irreducible SI base units.
- **SymPy Symbolic Validation**: Ensures algebraic equivalence regardless of variable positioning or constant inclusion (e.g., expressions with π or trigonometric functions).
- **Model-Assisted Semantic Fallback**: Leverages LLM evaluation for conceptual prose or circuit-localized field descriptions where exact string matching is insufficient.

---

## 🧠 MARJ Framework Alignment

Standard mathematical evaluation fails dramatically on physics datasets due to variations in how physical systems are described. This module implements the **MARJ** architecture:

1. **Rule-Based Judgment (R & J)**: Executes programmatic parsing of numerical values and unit bounds first, evaluating structural properties dynamically by reading experimental precision (significant figures) from the ground truth.
2. **Model-Assistant (M)**: When numerical or algebraic methods fail, passes the problem to a semantic evaluator to verify physical intuition using domain-specific terminology.

---

## 🗺️ Architecture & Evaluation Flow

The evaluation pipeline (`evaluate_physics_answer`) executes through a fallback cascade:

### Phase 1: Data Normalization
- Structures raw inputs into `_Item` dataclasses containing `value`, `unit`, and `raw_value` fields
- Handles dict, list, and primitive input formats
- Supports nested answer structures with multiple components
- Cleans micro-symbol variations (μ, mu, micro → u)
- Normalizes unit strings while preserving case sensitivity for metric prefixes

### Phase 2: Unit Conversion & Scaling
- Converts all numeric values to SI base units using Pint
- Handles metric prefixes (p, n, μ, m, k, M, G, T) with fallback parsing
- Resolves unit equivalencies (e.g., V/m ≡ N/C for electric fields)
- Preserves dimensional consistency across comparisons

### Phase 3: Multi-Layer Matching
Attempts to match model answers against correct answers using:

**Layer 1: Numerical Precision Matching**
- Extracts significant figures from correct answer's raw string format
- Validates against 2% relative error tolerance for basic cases
- Uses sig-fig-based absolute error bounds for scientific notation
- Handles zero-value edge cases with absolute threshold (1e-7)

**Layer 2: Symbolic Algebra Validation**
- Parses mathematical expressions into SymPy symbolic trees
- Supports multi-character variables (e.g., `q0`, `ke`, `mu_0`)
- Simplifies differences to check for algebraic equivalence
- Validates numeric expression differences below 1e-5 threshold

**Layer 3: String Matching**
- Performs case-insensitive exact string comparison
- Applies substring matching for qualitative text answers

### Phase 4: LLM Semantic Fallback
When rule-based methods fail on conceptual/textual answers:
- Extracts answers from raw model output if parsed field is empty
- Applies domain-specific equivalence rules for E&M and circuits:
  - **Conceptual Shorthand**: "inside the solenoid" ≡ "within the interior along its central axis"
  - **Physical Triggers**: "changing magnetic flux" ≡ "changing current" for self-induction
  - **Proportionality**: "increases" ≡ "increases in direct proportion" (unless non-linear)
  - **Permissible Extras**: Including fundamental constants doesn't invalidate correct variable lists
- Uses structured `<thinking>` + `Final Verdict: yes/no` output format
- Configurable via environment variables: `PHYSICS_EVAL_LLM_KEY`, `PHYSICS_EVAL_LLM_MODEL`

---

## 📚 API Reference

### Main Entry Point

#### `evaluate_physics_answer(question: str, model_answer: Any, model_raw_output: Optional[str], correct_answer: Any, *, llm_model: bool = False) -> bool`

Evaluates whether a model's answer matches the correct answer using multi-tiered validation.

**Parameters:**
- `question` (str): The physics question text (used for LLM context)
- `model_answer` (Any): Parsed answer from the solver. Supports:
  - Dict with `ans` and `unit` keys: `{"ans": 3.5, "unit": "m/s"}`
  - List of dicts: `[{"ans": 1.2, "unit": "V"}, {"ans": 3.4, "unit": "A"}]`
  - Primitive values: `42` or `"increasing"`
- `model_raw_output` (Optional[str]): Raw model response text, used as fallback if parsing fails
- `correct_answer` (Any): Ground truth in same format as `model_answer`
- `llm_model` (bool): Enable LLM semantic fallback for textual answers (default: False)

**Returns:**
- `bool`: True if answers match within tolerance, False otherwise

**Example:**
```python
from src.eval.eval_physics import evaluate_physics_answer

# Numeric answer with units
result = evaluate_physics_answer(
    question="What is the velocity?",
    model_answer={"ans": 3.14, "unit": "m/s"},
    model_raw_output=None,
    correct_answer={"ans": 3.1, "unit": "m/s"},
    llm_model=False
)  # Returns True (within sig-fig tolerance)

# Multiple answers
result = evaluate_physics_answer(
    question="Find voltage and current",
    model_answer=[{"ans": 12, "unit": "V"}, {"ans": 2.5, "unit": "A"}],
    model_raw_output=None,
    correct_answer=[{"ans": 12, "unit": "V"}, {"ans": 2.5, "unit": "A"}],
    llm_model=False
)  # Returns True

# Symbolic expression
result = evaluate_physics_answer(
    question="Express force in terms of q and E",
    model_answer={"ans": "q*E", "unit": "N"},
    model_raw_output=None,
    correct_answer={"ans": "E*q", "unit": "N"},
    llm_model=False
)  # Returns True (algebraically equivalent)

# Conceptual answer with LLM fallback
result = evaluate_physics_answer(
    question="Where is the magnetic field strongest?",
    model_answer={"ans": "inside the solenoid", "unit": ""},
    model_raw_output="The field is strongest inside the solenoid.",
    correct_answer={"ans": "within the interior along its central axis", "unit": ""},
    llm_model=True
)  # Returns True (semantically equivalent via LLM)
```

---

### Internal Helper Functions

#### `_normalize_items(payload: dict | list | str | Any) -> List[_Item]`
Flattens arbitrary input formats into normalized `_Item` dataclass instances.

#### `_convert_to_si(value: float, unit: str) -> Tuple[float, str]`
Converts values to SI base units using Pint, with fallback metric prefix handling.

#### `_get_sig_figs(raw_val: str) -> Optional[int]`
Extracts significant figures from raw answer strings (e.g., "8.2e3" → 2 sig figs).

#### `_numeric_match(model_item: _Item, correct_item: _Item) -> bool`
Validates numeric answers using sig-fig-based precision and 2% relative error tolerance.

#### `_symbolic_match(model_item: _Item, correct_item: _Item) -> bool`
Checks algebraic equivalence using SymPy symbolic simplification.

#### `_llm_or_text_match(question: str, model_text: str, correct_text: str, model_raw_output: Optional[str], llm_model: bool) -> bool`
Final fallback for textual answers using string normalization and optional LLM evaluation.

---

## ⚙️ Configuration

### Environment Variables

```bash
# LLM fallback configuration (optional, only used if llm_model=True)
PHYSICS_EVAL_LLM_KEY=your-api-key-here
PHYSICS_EVAL_LLM_MODEL=gpt-4-0613  # or other model identifier
```

### Dependencies

```python
sympy>=1.12       # Symbolic mathematics
pint>=0.23        # Unit conversion and dimensional analysis
python-dotenv     # Environment variable management (optional)
```

---

## 🔬 Testing & Validation

The evaluator is designed to handle:
- ✅ Scientific notation variations (`3.5e2`, `3.5 * 10^2`, `3.5x10^2`)
- ✅ Unit prefix aliases (`μF`, `muF`, `uF` all map to microfarads)
- ✅ Dimensional equivalencies (`V/m` = `N/C` for electric fields)
- ✅ Algebraic reordering (`q*E` = `E*q`)
- ✅ Multi-part answers with different units
- ✅ Text-based conceptual answers via LLM
- ✅ LaTeX fraction parsing (`\frac{1}{2}` → 0.5)

---

## 📊 Accuracy Considerations

**When to use `llm_model=True`:**
- Answers involve qualitative descriptions (e.g., "magnetic field direction")
- Circuit topology descriptions (e.g., "parallel to the plates")
- Conceptual explanations where phrasing varies but meaning is identical

**When to keep `llm_model=False`:**
- Pure numeric answers with units
- Mathematical expressions with variables
- Any answer where rule-based validation is sufficient (faster and deterministic)

**Known Limitations:**
- LLM fallback requires API access and adds latency (~1-3s per call)
- Sig-fig extraction assumes standard scientific notation formatting
- Unit conversion limited to Pint's registry (exotic units may need manual mapping)
- Multi-character variables in symbolic expressions must not contain spaces