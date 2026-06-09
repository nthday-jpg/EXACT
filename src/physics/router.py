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
    raise FileNotFoundError(f"Router configuration not found at {config_path}")

def _extract_json_object(content: str) -> str | None:
    content = (content or "").strip()
    if not content:
        return None
    if content.startswith("{") and content.endswith("}"):
        return content
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = content[start : end + 1].strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        return candidate
    return None


class QuestionClassification:
    """Output from router classification."""
    
    def __init__(self, domains: List[str], warnings: List[str] = []):
        self.domains = domains  # e.g., ["electrostatics", "geometry"]
        self.warnings = warnings 

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
    Assumes question is already preprocessed
    
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
        response = client.generate(classification_prompt, max_tokens=1024)
        content = response.get("content", "")
    except Exception as e: 
        print(f"[router] classify fallback due to API error: {e}")
        return QuestionClassification([])

    try:
        json_text = _extract_json_object(content)
        if not json_text:
            raise json.JSONDecodeError("No JSON object found", content, 0)
        classification_json = json.loads(json_text)
        domains = classification_json.get("domains", [])
        multi_state = classification_json.get("multi_state", False)
        
        if not isinstance(domains, list):
            domains = [domains]
        if not isinstance(multi_state, bool):
            multi_state = False
        
        if multi_state:
            # Add warning about multi-state questions
            warning = "Keep variables from distinct physical states separate. Do not solve incompatible state equations simultaneously."
            return QuestionClassification(domains, warnings=[warning])
        
        return QuestionClassification(domains)
    except json.JSONDecodeError:
        print(f"[router] classify fallback due to JSON parsing error")
        return QuestionClassification([])