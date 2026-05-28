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

def main():
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-api.modal.run"
    base_url = f"{modal_url}/v1"
    model_name = "exact-qwen3-8b"
    api_key = "modal-placeholder"

    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        use_local=False,
    )

    combined_nl = [
      "If a student completes all required courses, they are eligible for graduation.",
      "If a student is eligible for graduation and maintains a GPA above 3.5, they graduate with honors.",
      "If a student graduates with honors and completes a thesis, they receive academic distinction.",
      "If a student receives academic distinction, they qualify for the graduate fellowship program.",
      "John has completed all required courses.",
      "John maintains a GPA of 3.8.",
      "John has completed a thesis.",
      "John qualifies for the graduate fellowship program",
      "John needs faculty recommendation for the fellowship",
      "John must complete an internship to qualify",
      "John’s GPA is insufficient for honors"
    ]

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
    for i, nl in enumerate(combined_nl, start=1):
        nl_content += f"{i}. {nl}\n"

    user_prompt = (
        "Convert the following premises into canonical first-order logic.\n\n"
        "Premises:\n"
        f"{nl_content.strip()}\n\n"
        "Return a JSON list of strings containing the formulas."
    )

    print("Translating combined MCQ list...")
    response = client.generate_text(prompt=user_prompt, system_prompt=system_prompt, max_new_tokens=1024)
    print("\n--- Model Response ---")
    print(response)

if __name__ == "__main__":
    main()
