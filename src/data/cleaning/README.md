# 🛠️ Automated FOL Logical Dataset Validation & Repair Pipeline

This package provides a production-grade, highly automated pipeline to validate, clean, and auto-repair logical reasoning datasets under **First-Order Logic (FOL)** grammar constraints and the **Z3 SMT Solver**.

---

## 🚀 Features

- **Strict Z3 Validation**: Ensures FOL syntax is 100% compliant with the custom Z3-backed logic verifier, preventing solver crashes and runtime errors.
- **Automated Self-Correction**: Implements a multi-turn dialogue with the `Qwen3-235B` model, providing raw Z3 parsing errors directly as conversational feedback to automatically correct logical flaws.
- **Robust Math Translation**: Safely translates division, multiplication, percentages, and arithmetic equations into qualitative, uninterpreted predicate representations to avoid solver non-linear limitations.
- **Executable CLI**: Run validation and auto-repair directly from the terminal.
- **Developer API**: Import and run the pipeline from any module or script.

---

## 📐 Strict Logical Parser & Grammar Rules

To pass validation successfully, FOL formulas must conform to the following architectural rules:

### 1. Nested Quantifiers Only
- Quantifiers like `ForAll` and `Exists` must qualify exactly **one** variable at a time.
- Multiple variables must be nested sequentially. No list brackets `[]` are allowed.
  - **CORRECT**: `ForAll(x, ForAll(y, P(x, y)))`
  - **INCORRECT**: `ForAll([x, y], P(x, y))` or `ForAll(x, y, P(x, y))`

### 2. Uppercase Connectives
- All logical connectives must be strictly uppercase.
  - **Connectives**: `AND`, `OR`, `NOT`, `->`, `<->`
  - **CORRECT**: `P(x) -> (Q(x) AND NOT R(x))`

### 3. No Multiplications or Divisions
- The logic parser does **not** support operators like `*` or `/`.
- All arithmetic formulas and weighted calculations must be mapped qualitatively using uninterpreted predicates or functions.
  - **Example (Credits ratio)**: Replace `65 * TotalCredits(Program(s)) / 100` with `InternshipRequiredCredits(Program(s))`.
  - **Example (Forgetting curve)**: Replace `Retention(s, t) = e AND (-t/S)` with `ForgettingCurve(s, t, S)`.

### 4. Zero-Arity Predicates
- Any predicate with zero arguments must be explicitly declared with empty parentheses `()` so the parser instantiates it as a boolean relation.
  - **CORRECT**: `depleted_fund()`, `lack_partnerships()`
  - **INCORRECT**: `depleted_fund`, `lack_partnerships`

### 5. String Constants / Quotes
- Do not use single quotes around string constants (e.g. `'a+'`, `'Junior'`). The parser treats single quotes as String sort, causing sort mismatches against the uninterpreted domain sort `U`.
  - **CORRECT**: `Grade(aplus)`, `Status(Ha, Junior)`
  - **INCORRECT**: `Grade('a+')`, `Status(Ha, 'Junior')`

### 6. Function Equalities
- Non-numeric function equality statements (e.g., `Program(Vinh) = TrainingProgram`) returning uninterpreted constants cause sort mismatches. Convert them into binary relation predicates.
  - **CORRECT**: `Program(Vinh, TrainingProgram)`
  - **INCORRECT**: `Program(Vinh) = TrainingProgram`

---

## 💻 CLI Usage

You can run the pipeline directly using the executable package syntax:

```bash
python -m src.data \
  --input data/processed/merged_invalid.json \
  --output-valid data/processed/merged_valid.json \
  --output-invalid data/processed/merged_invalid.json \
  --retries 3
```

### Options

| Flag | Long Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `-i` | `--input` | **(Required)** Path to the input JSON dataset | None |
| `-v` | `--output-valid` | **(Required)** Path to write the Z3-valid samples | None |
| `-x` | `--output-invalid`| **(Required)** Path to write the Z3-invalid samples | None |
| | `--no-repair` | Disable LLM-assisted repair (validation only) | `False` |
| `-m` | `--model` | LLM model used for automated repair | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| `-p` | `--provider` | API routing provider | `together` |
| `-r` | `--retries` | Max conversational repair attempts per sample | `3` |

---

## 🐍 Python API Usage

The pipeline can be imported and executed programmatically:

```python
from src.data import LogicalDatasetPipeline

# 1. Initialize pipeline
pipeline = LogicalDatasetPipeline(
    model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
    temperature=0.1
)

# 2. Programmatically validate a single logic sample
is_valid, error = pipeline.validate_sample_fol([
    "Student(Ha)",
    "ForAll(x, Student(x) -> Eligible(x))"
])
print("Is Valid:", is_valid)

# 3. Execute full file pipeline
pipeline.run_pipeline(
    input_path="data/processed/merged_invalid.json",
    output_valid_path="data/processed/merged_valid.json",
    output_invalid_path="data/processed/merged_invalid.json",
    auto_repair=True
)
```
