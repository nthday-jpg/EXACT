# Normalization utilities

This module centralizes normalization for both logic and physics data.

## Logic normalization

Functions:
- normalize_logic_premise_text(text):
  - Normalizes unicode punctuation and whitespace.
  - Collapses titles into single tokens ("Dr. Zee" -> "DrZee", "Dr John Smith" -> "DrJohnSmith").
  - Normalizes temperatures ("25 °C" -> "25C").
  - Normalizes times ("9 AM" -> "Time9AM", "10:30 PM" -> "Time1030PM").
  - Normalizes durations ("24 hours" -> "Duration24Hours").
  - Removes apostrophes to avoid parser issues ("Master's" -> "Masters").
- normalize_logic_fol_entry(text):
  - Normalizes quantifiers to `ForAll(x, ...)` / `Exists(x, ...)`.
  - Replaces unicode logic operators with ASCII tokens.
  - Ensures `NOT` is separated from parentheses.
  - Closes unmatched parentheses to keep parser compatibility.
- extract_fol_formulas(text):
  - Extracts FOL formula strings from conversational or formatted model responses.
  - Handles markdown code fences and JSON lists, falling back to line-by-line analysis.
  - Strips `<think>...</think>` tags before parsing.
- unify_fol_predicates(formulas):
  - Lexically unifies predicate names across translated formulas to resolve naming and capitalization mismatches.
  - Splits snake_case/camelCase predicate names, strips domain-generic filler words (e.g. `project`, `requirement`), and reformats them to standardized PascalCase.

## Physics normalization

Functions:
- normalize_physics_input(text):
  - Normalizes unicode whitespace, minus, multiply, and fractions.
  - Preserves formatting suitable for prompts.
- normalize_physics_output(text):
  - Applies input normalization plus unit normalization and equation spacing.
  - Converts common fractions to decimals.
- normalize_physics_scientific_text(text):
  - Normalizes scientific notation from superscripts and unicode multiply.
  - Converts powers to `e` notation (e.g. `2e5`) and standardizes spacing.
- extract_value_unit_explanation(text):
  - Extracts a numeric value, unit, and qualitative explanation from normalized strings.

## Notes

- Logic normalization is intended for premise text and FOL strings only.
- Physics normalization is intended for numeric QA prompts and outputs.
- Lexical predicate unification is critical to prevent solver failures due to naming inconsistencies.
