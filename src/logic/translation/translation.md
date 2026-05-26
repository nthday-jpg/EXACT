# First-Order Logic (FOL) Translation Module

This module handles the translation of natural language (NL) premises and conclusions into standardized First-Order Logic (FOL) formulas using large language models.

## Components

- **pipeline.py**: Contains the `NLToFOLPipeline` class. It manages loading LLMs, preparing structured prompts, querying the model, and extracting FOL list formulas from raw model responses.

## Key Features

- **Execution Flexibility**: Supports local loading of fine-tuned PEFT LoRA adapter models with NF4 quantization (optimized for low-resource hardware) as well as calling remote API instances via `LLMClient`.
- **Predicate Alignment Prompting**: System and user prompts enforce strict constraints to ensure uniform predicate definitions and canonical operator formatting (e.g., standardizing custom symbols into parser-safe operators like `AND`, `OR`, `ForAll`, `Exists`).
- **Robust Output Recovery**: Utilizes regular expressions and JSON parsers in `extract_fol_formulas` to reliably extract and align logic formulas even from conversational or verbose model responses.

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

# Translate to FOL formulas
premises_fol, conclusion_fol = translator.translate_premises_and_conclusion(
    premises_nl, 
    conclusion_nl
)

print("Premises FOL:", premises_fol)
# Output: ['ForAll(x, (Completes(x, Course_A) -> CanEnroll(x, Course_B)))', 'Completes(Sophia, Course_A)']
print("Conclusion FOL:", conclusion_fol)
# Output: 'CanEnroll(Sophia, Course_B)'
```
