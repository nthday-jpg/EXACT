from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.llm.llm_client import LLMClient


def _load_router_config() -> str:
    """Load router configuration from instructions/router.md."""
    config_path = Path(__file__).parent / "instructions" / "router.md"
    if config_path.exists():
        return config_path.read_text(encoding="utf-8")
    return ""


class QuestionClassification:
    """Output from router classification."""
    
    def __init__(self, domains: List[str], question_type: str, warnings: List[str] = None):
        self.domains = domains  # e.g., ["electrostatics", "geometry"]
        self.question_type = question_type  # "Numerical", "Formula", or "Qualitative"
        self.warnings = warnings or []  # Optional warnings about classification issues

def classify_question(
    question: str,
    *,
    model_name: str,
    api_key: str,
    base_url: str | None = None,
    temperature: float = 0.0,
) -> QuestionClassification:
    """
    Route a physics question using LLM to classify domains and type.
    
    Returns JSON with:
    {
        "domains": ["electrostatics", "geometry", ...],
        "question_type": "Numerical" | "Formula" | "Qualitative",
        "multi_state": true | false
    }
    
    Configuration loaded from: src/physics/instructions/router.md
    """
    config = _load_router_config()
    
    client = LLMClient(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url or "https://router.huggingface.co/v1",
        system_prompt=config,
        temperature=temperature,
        enable_thinking=False,
    )
    classification_prompt = "<QUESTION>\n" + question.strip() + "\n</QUESTION>"
    try:
        response = client.generate(classification_prompt, max_tokens=128)
        content = response.get("content", "")
    except Exception as e: 
        print(f"[router] classify fallback due to API error: {e}")
        return QuestionClassification(["electrostatics", "geometry"], "Numerical")

    try:
        classification_json = json.loads(content.strip())
        domains = classification_json.get("domains", [])
        question_type = classification_json.get("question_type", "Numerical")
        multi_state = classification_json.get("multi_state", False)
        
        if not isinstance(domains, list):
            domains = [domains]
        if question_type not in ("Numerical", "Formula", "Qualitative"):
            question_type = "Numerical"
        if not isinstance(multi_state, bool):
            multi_state = False
        
        if multi_state:
            # Add warning about multi-state questions
            warning = "Keep variables from distinct physical states separate. Do not solve incompatible state equations simultaneously."
            return QuestionClassification(domains, question_type, warnings=[warning])
        
        return QuestionClassification(domains, question_type)
    except json.JSONDecodeError:
        # Fallback: return generic classification
        return QuestionClassification(["electrostatics", "geometry"], "Numerical")
