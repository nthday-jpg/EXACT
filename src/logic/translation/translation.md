# First-Order Logic (FOL) Translation Module

This module handles the translation of natural language (NL) premises and conclusions into standardized First-Order Logic (FOL) formulas using large language models, with an automatic repair loop to fix broken formulas.

## Components

- **`pipeline.py`**: Contains the `NLToFOLPipeline` class. Manages LLM loading, structured prompt preparation, model querying, FOL extraction, and post-generation formula validation/repair.

## Key Features

- **Execution Flexibility**: Supports local loading of fine-tuned PEFT LoRA adapter models with NF4 4-bit quantization (optimized for low-resource hardware) as well as calling remote API instances via `LLMClient`.
- **Glossary-Constrained Translation (Two-Stage)** *(new)*: To ensure 100% uniform predicate and entity mapping across premises, it first runs a Glossary Generation stage to define a JSON dictionary of predicates/constants. The second stage translates statements strictly aligned under these constraints.
- **FOL Automatic Normalization** *(new)*: Extracted formulas are immediately normalized using `normalize_logic_fol_entry` to automatically repair minor syntax/casing issues (e.g. `forall` vs `ForAll`, spaces, or operators like `&`/`~`), preventing redundant LLM calls.
- **Robust Output Recovery**: Utilizes regular expressions and JSON parsers in `extract_fol_formulas` to reliably extract and align logic formulas even from conversational or verbose model responses.
- **FOL Repair Loop**: After generation and normalization, each formula is validated by attempting a Z3 parse (`try_parse_fol`). Any remaining broken formulas are automatically sent back to the LLM with the exact parse error for correction — up to 2 retries per formula.

## Public API

### `translate_list(nl_list) -> list[str]`
Translates a list of NL sentences into FOL formulas in a two-stage glossary-constrained flow, then automatically normalizes, validates, and repairs each formula.

### `generate_glossary(nl_list) -> dict | None` *(new)*
Analyzes the list of statements and outputs a unified JSON Glossary of predicates and constants.

### `translate_premises_and_conclusion(premises_nl, conclusion_nl) -> (list[str], str)`
Convenience wrapper around `translate_list` that splits the result into premises and conclusion.

### `_repair_fol(formula, error) -> str` *(internal)*
Sends a broken formula and its parse error back to the LLM for correction. Returns the repaired formula string.

### `_validate_and_repair(formulas, max_retries=2) -> list[str]` *(internal)*
Iterates over each formula, calls `try_parse_fol`, and triggers `_repair_fol` for any that fail. Candidate repairs are automatically normalized and re-validated. Accepts the best available version after `max_retries` attempts.

## Basic Usage

```python
from src.logic.translation.pipeline import NLToFOLPipeline

# Initialize the translation pipeline
translator = NLToFOLPipeline(use_local=False, llm_client=your_llm_client)

premises_nl = [
    "If a student completes Course A, they can enroll in Course B.",
    "Sophia completed Course A."
]
conclusion_nl = "Sophia can enroll in Course B."

# Translate to FOL formulas (includes automatic repair)
premises_fol, conclusion_fol = translator.translate_premises_and_conclusion(
    premises_nl,
    conclusion_nl
)

print("Premises FOL:", premises_fol)
# ['ForAll(x, (Completes(x, Course_A) -> CanEnroll(x, Course_B)))', 'Completes(Sophia, Course_A)']
print("Conclusion FOL:", conclusion_fol)
# 'CanEnroll(Sophia, Course_B)'
```

## FOL Repair Loop Detail

```
translate_list()
    │
    ├─ LLM generates FOL strings
    │
    └─ _validate_and_repair()
           ├─ Formula OK → keep as-is
           └─ Formula broken
                   ├─ Retry 1: _repair_fol(formula, error) → LLM fix → revalidate
                   └─ Retry 2: repeat if still broken → keep best available
```

## Allowed Operators (enforced in prompts)

```
AND  OR  NOT  ->  <->  =  !=  >=  <=  >  <  ForAll  Exists
```

Quantifier syntax: `ForAll(x, <body>)` or `Exists(x, <body>)`.  
Predicate syntax: `P(x)`, `R(a, b)` — no spaces before `(`.
