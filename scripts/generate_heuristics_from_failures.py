from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agents.exploration.generation import generate_heuristics_with_llm


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Use DEFAULT_MODEL as fallback for all LLMs
    default_model = os.getenv("DEFAULT_MODEL", "gemini-3.5-flash")
    model = os.getenv("PHYSICS_MODEL") or default_model
    base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    
    # Load generation instruction as system prompt
    instruction_path = Path("src/agents/exploration/generation_instruction.md")
    if instruction_path.exists():
        system_prompt = instruction_path.read_text(encoding="utf-8")
    else:
        system_prompt = os.getenv(
            "PHYSICS_HEURISTICS_SYSTEM",
            "You are a physics evaluator. Produce concise heuristics to fix failure patterns."
        )

    failures_path = Path("runs/physics_failures.json")
    output_path = Path("runs/physics_heuristics.md")

    if not failures_path.exists():
        raise FileNotFoundError(str(failures_path))

    failures = json.loads(failures_path.read_text("utf-8"))
    if not isinstance(failures, list):
        raise ValueError("failures file must contain a list")

    content = generate_heuristics_with_llm(
        failures=failures,
        model_name=model,
        api_key=api_key,
        base_url=base_url,
        system_prompt=system_prompt,
        chunk_size=10,
        temperature=0.1,
        enable_thinking=False,
        verbose=True,
    )
    output_path.write_text(content, encoding="utf-8")

    print(f"Loaded {len(failures)} failures")
    print(f"Wrote heuristics to {output_path}")


if __name__ == "__main__":
    main()
