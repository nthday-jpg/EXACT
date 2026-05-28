"""Smoke tests for the recent logic pipeline fixes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.normalization import normalize_logic_fol_entry, extract_fol_formulas

# Test 1: Think tag stripping (space-padded variant like Qwen3 generates)
contaminated = "< think > some thinking here < /think > Human(Socrates)"
result = normalize_logic_fol_entry(contaminated)
print("Test 1 (think tag strip):", repr(result))
assert "think" not in result.lower(), "think tag not stripped!"
assert "Human" in result
print("  PASS")

# Test 2: Extract FOL with think tag (standard no-space)
text_with_think = '<think> reasoning </think> ["ForAll(x, Human(x) -> Mortal(x))"]'
formulas = extract_fol_formulas(text_with_think)
print("Test 2 (extract with think):", formulas)
assert len(formulas) > 0
assert "think" not in str(formulas).lower()
print("  PASS")

# Test 3: Extract FOL with space-padded think tag
text_with_spaced = '< think > reasoning < /think > ["Human(Socrates)"]'
formulas2 = extract_fol_formulas(text_with_spaced)
print("Test 3 (extract with spaced think):", formulas2)
assert len(formulas2) > 0
assert "think" not in str(formulas2).lower()
print("  PASS")

# Test 4: Semantic fallback prompts importable
from src.llm.prompts import (
    SEMANTIC_YESNO_SYSTEM_PROMPT, SEMANTIC_YESNO_USER_PROMPT_TEMPLATE,
    SEMANTIC_MCQ_SYSTEM_PROMPT, SEMANTIC_MCQ_USER_PROMPT_TEMPLATE,
)
assert "{premises_text}" in SEMANTIC_YESNO_USER_PROMPT_TEMPLATE
assert "{conclusion_nl}" in SEMANTIC_YESNO_USER_PROMPT_TEMPLATE
assert "{premises_text}" in SEMANTIC_MCQ_USER_PROMPT_TEMPLATE
assert "{question_nl}" in SEMANTIC_MCQ_USER_PROMPT_TEMPLATE
print("Test 4 (prompt imports):", "PASS")

# Test 5: Pipeline imports correctly
from src.logic.pipeline import LogicalReasoningPipeline
print("Test 5 (pipeline import):", "PASS")

print("\nAll smoke tests passed!")
