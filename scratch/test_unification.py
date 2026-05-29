import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

load_dotenv()

from src.llm.llm_client import LLMClient
from src.utils.normalization import extract_fol_formulas

def main():
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run"
    base_url = f"{modal_url}/v1"
    model_name = "exact-qwen3-8b"
    api_key = "modal-placeholder"

    print("Initializing LLMClient...")
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        use_local=False,
    )

    formulas = [
      "ForAll(x, (WellTested(x) -> Optimized(x))))",
      "ForAll(x, (NOT FollowsPEP8(x)) -> NOT WellTested(x))))",
      "ForAll(x, EasyToMaintain(x)))",
      "ForAll(x, WellTested(x)))",
      "ForAll(x, (FollowsPEP8(x)) -> EasyToMaintain(x))))",
      "ForAll(x, (WellTested(x)) -> FollowsPEP8(x))))",
      "ForAll(x, (WellStructuredProject(x)) -> OptimizedProject(x))))",
      "ForAll(x, (EasyToMaintainProject(x)) -> WellTestedProject(x))))",
      "ForAll(x, (OptimizedProject(x)) -> CleanReadableCodeProject(x))))",
      "ForAll(x, WellStructuredProject(x)))",
      "ForAll(x, CleanReadableCodeProject(x)))",
      "ExistsAtLeastOneBestPracticePythonProject())",
      "ExistsAtLeastOneOptimizedPythonProject())",
      "ForAll(p, NOT WellStructuredPythonProject(p)) -> NOT FollowsPEP8PythonProject(p))))"
    ]

    print("\n--- Initial Formulas ---")
    for i, f in enumerate(formulas, 1):
        print(f"{i}. {f}")

    unify_system_prompt = (
        "You are a formal logic refactoring assistant.\n"
        "Your task is to analyze a list of First-Order Logic (FOL) formulas and unify their predicate and constant names "
        "so that identical concepts use the exact same name across all formulas.\n\n"
        "STRICT RULES:\n"
        "1. Identify concepts that are lexically or semantically the same but named slightly differently (e.g., 'WellTested(x)', 'WellTestedProject(x)', 'WellTestedPythonProject(x)'). Choose a single, short canonical predicate name (like 'WellTested(x)') and rewrite all occurrences to use that name.\n"
        "2. Do the same for constants (e.g., 'Sophia' vs 'sophia').\n"
        "3. Preserve the exact logical operators (AND, OR, NOT, ->, <->, ForAll, Exists, =, etc.) and the structure/nesting of all quantifiers and parentheses.\n"
        "4. Output a STRICT valid JSON list of strings containing the refactored formulas in the exact same order.\n"
        "Return JSON only. Do not include explanation."
    )

    user_prompt = (
        "Refactor and unify the predicates/constants in the following FOL formulas:\n\n"
        f"{json.dumps(formulas, indent=2)}\n\n"
        "Return the unified list as a strict JSON list of strings."
    )

    print("\nSending request to model for predicate unification...")
    response = client.generate_text(prompt=user_prompt, system_prompt=unify_system_prompt, max_new_tokens=2048)
    print("\n--- Response from Model ---")
    print(response)

    print("\n--- Extracted Unified Formulas ---")
    unified_formulas = extract_fol_formulas(response)
    for i, f in enumerate(unified_formulas, 1):
        print(f"{i}. {f}")

if __name__ == "__main__":
    main()
