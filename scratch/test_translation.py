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
from src.logic.reasoning.verifier import try_parse_fol
from src.utils.normalization import normalize_logic_fol_entry

def main():
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run"
    base_url = f"{modal_url}/v1"
    model_name = "exact-qwen3-8b"
    api_key = "modal-placeholder"

    print(f"Initializing LLMClient with Model: {model_name} at {base_url}...")
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        use_local=False,
    )

    # Sample premises from logic_based.json
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
      "If a Python project is not well-structured, then it does not follow PEP 8 standards."
    ]

    print("\n--- NL Premises ---")
    for i, p in enumerate(premises_nl, 1):
        print(f"{i}. {p}")

    # Build the exact prompt used in finetuning
    system_prompt = (
        "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
        "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n\n"
        "ALLOWED OPERATORS:\n"
        "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
        "QUANTIFIER RULES:\n"
        "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
        "Return JSON only."
    )

    nl_content = ""
    for i, nl in enumerate(premises_nl, start=1):
        nl_content += f"{i}. {nl}\n"

    user_prompt = (
        "Convert the following premises into canonical first-order logic.\n\n"
        "Premises:\n"
        f"{nl_content.strip()}\n\n"
        "Return a JSON list of strings containing the formulas."
    )

    print("\nSending request to finetuned model...")
    response = client.generate_text(prompt=user_prompt, system_prompt=system_prompt, max_new_tokens=1024)
    print("\n--- Raw Response from Model ---")
    print(response)

    print("\n--- Parsability and Casing Verification ---")
    try:
        formulas = json.loads(response.strip())
        for idx, formula in enumerate(formulas, 1):
            normalized = normalize_logic_fol_entry(formula)
            ok, err = try_parse_fol(normalized)
            status = "PASS 🟢" if ok else f"FAIL 🔴 (Error: {err})"
            print(f"Formula {idx}: {formula}  -> Normalized: {normalized}  -> Status: {status}")
    except Exception as e:
        print(f"Failed to parse response as JSON: {str(e)}")

if __name__ == "__main__":
    main()
