"""
Debug script for S0Q1: Does it follow that if all Python projects are well-structured,
then all Python projects are optimized, according to the premises?
Expected answer: Yes (Z3 should return unsat)

Run: .venv/Scripts/python.exe scratch/debug_s0q1.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))
load_dotenv()

from src.logic.pipeline import LogicalReasoningPipeline
from src.llm.llm_client import LLMClient
from src.logic.reasoning.verifier import verify_with_z3

MODAL_URL = "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run"

premises_nl = [
    "If a Python code is well-tested, then the project is optimized.",
    "If a Python code does not follow PEP 8 standards, then it is not well-tested.",
    "All Python projects are easy to maintain.",
    "All Python code is well-tested.",
    "If a Python code follows PEP 8 standards, then it is easy to maintain.",
    "If a Python code is well-tested, then it follows PEP 8 standards.",
    "If a Python project is well-structured, then it is optimized.",
    "If a Python project is easy to maintain, then it is well-tested.",
    "If a Python project is optimized, then it has clean and readable code.",
    "All Python projects are well-structured.",
    "All Python projects have clean and readable code.",
    "There exists at least one Python project that follows best practices.",
    "There exists at least one Python project that is optimized.",
    "If a Python project is not well-structured, then it does not follow PEP 8 standards.",
]

conclusion_nl = "Does it follow that if all Python projects are well-structured, then all Python projects are optimized, according to the premises?"

# Ground-truth FOL premises (from dataset)
premises_fol_gt = [
    "∀x (WT(x) → O(x))",
    "∀x (¬PEP8(x) → ¬WT(x))",
    "∀x (EM(x))",
    "∀x (WT(x))",
    "∀x (PEP8(x) → EM(x))",
    "∀x (WT(x) → PEP8(x))",
    "∀x (WS(x) → O(x))",
    "∀x (EM(x) → WT(x))",
    "∀x (O(x) → CR(x))",
    "∀x (WS(x))",
    "∀x (CR(x))",
    "∃x (BP(x))",
    "∃x (O(x))",
    "∀x (¬WS(x) → ¬PEP8(x))",
]
conclusion_fol_gt = "∀x (WS(x) → O(x))"

print("=" * 60)
print("STEP 1: Test with ground-truth FOL (dataset gold standard)")
print("=" * 60)
result_gt = verify_with_z3(premises_fol_gt, conclusion_fol_gt, negate_conclusion=True)
print(f"Z3 result (GT FOL): {result_gt['result']}")
if result_gt.get("error"):
    print(f"Z3 error: {result_gt['error']}")
print()

print("=" * 60)
print("STEP 2: Run full pipeline translation")
print("=" * 60)

client = LLMClient(
    model_name="exact-qwen3-8b",
    api_key="modal-placeholder",
    base_url=f"{MODAL_URL}/v1",
    temperature=0.1,
    frequency_penalty=0.0,
    use_local=False,
)

pipeline = LogicalReasoningPipeline(llm_client=client)

# Test translate_list with all 14 premises
print(f"Translating {len(premises_nl)} premises + 1 conclusion = {len(premises_nl)+1} total sentences...")
print(f"Using unified call (max_new_tokens=1024)...")
all_nl = premises_nl + [conclusion_nl]
all_fol_1024 = pipeline.translation_pipeline.translate_list(all_nl)
print(f"Result: {len(all_fol_1024)} formulas (expected {len(all_nl)})")
for i, fol in enumerate(all_fol_1024):
    tag = "P" if i < len(premises_nl) else "CONCLUSION"
    print(f"  [{tag}] {fol}")
print()

if len(all_fol_1024) != len(all_nl):
    print(f"Mismatch! Retrying with 2048 tokens...")
    all_fol_2048 = pipeline.translation_pipeline.translate_list(all_nl, max_new_tokens=2048)
    print(f"Result: {len(all_fol_2048)} formulas (expected {len(all_nl)})")
    for i, fol in enumerate(all_fol_2048):
        tag = "P" if i < len(premises_nl) else "CONCLUSION"
        print(f"  [{tag}] {fol}")
    print()

print("=" * 60)
print("STEP 3: translate_premises_and_conclusion (for Yes/No Q)")
print("=" * 60)
p_fol, c_fol = pipeline.translation_pipeline.translate_premises_and_conclusion(premises_nl, conclusion_nl)
print(f"Premises FOL ({len(p_fol)} formulas):")
for i, fol in enumerate(p_fol):
    print(f"  {i+1:2d}. {fol}")
print(f"\nConclusion FOL: {c_fol}")
print()

print("=" * 60)
print("STEP 4: Z3 verification with pipeline-translated FOL")
print("=" * 60)
result_pipeline = verify_with_z3(p_fol, c_fol, negate_conclusion=True)
print(f"Z3 result (pipeline FOL): {result_pipeline['result']}")
if result_pipeline.get("error"):
    print(f"Z3 error: {result_pipeline['error']}")
if result_pipeline.get("unsat_core"):
    print(f"Unsat core: {result_pipeline['unsat_core']}")
