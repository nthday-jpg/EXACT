from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.llm.llm_client import LLMClient
from src.physics.llm_execution import execute_llm_code
from src.physics.preprocessing import preprocess
from src.physics.types import PhysicsResult, PhysicsTask


class PhysicsSolver:
    def __init__(
        self,
        *,
        model_name: str,
        api_key: Optional[str],
        system_prompt: str,
        heuristic_prompt: Optional[str] = None,
        temperature: float = 0.1,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key or ""
        self._system_prompt = system_prompt
        self._heuristic_prompt = heuristic_prompt or ""
        self._temperature = temperature
        self._extra_body = extra_body or {}

    def solve(self, task: PhysicsTask) -> PhysicsResult:
        start = time.time()
        prompt = preprocess(task.question)
        if self._heuristic_prompt:
            prompt = f"{self._heuristic_prompt}\n\n{prompt}"

        client = LLMClient(
            model_name=self._model_name,
            api_key=self._api_key,
            system_prompt=self._system_prompt,
            temperature=self._temperature,
            extra_body=self._extra_body,
        )
        response = client.generate(prompt)
        content, tokens = _extract_content_and_tokens(response)

        model_answer = None
        error = None
        try:
            ans, unit = execute_llm_code(content)
            if ans is not None:
                model_answer = {"ans": ans, "unit": unit}
        except Exception as exc:  # pragma: no cover - safety fallback
            error = str(exc)

        elapsed = time.time() - start
        return PhysicsResult(
            task=task,
            model_answer=model_answer,
            raw_response=content,
            error=error,
            tokens=tokens,
            elapsed_s=elapsed,
        )


def _extract_content_and_tokens(response: Any) -> tuple[str, Optional[Dict[str, Any]]]:
    if isinstance(response, dict):
        content = str(response.get("content") or "")
        tokens = {
            "total_tokens": response.get("total_tokens"),
            "input_tokens": response.get("input_tokens"),
            "output_tokens": response.get("output_tokens"),
        }
        return content, tokens
    return str(response), None
