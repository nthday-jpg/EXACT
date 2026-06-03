from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.llm.llm_client import LLMClient
from src.physics.llm_execution import execute_llm_code
from src.physics.postprocessing import postprocess_answer
from src.physics.preprocessing import preprocess
from src.physics.types import PhysicsResult, PhysicsTask


class PhysicsSolver:
    def __init__(
        self,
        *,
        model_name: str,
        api_key: Optional[str],
        base_url: Optional[str] = None,
        system_prompt: str,
        solver_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = False,
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key or ""
        self._base_url = base_url
        self._system_prompt = system_prompt
        self._solver_prompt = solver_prompt or ""
        self._temperature = temperature
        self._max_tokens = max_tokens or 1024
        self._enable_thinking = enable_thinking

    def solve(self, task: PhysicsTask) -> PhysicsResult:
        start = time.time()
        prompt = preprocess(task.question)
        if self._solver_prompt:
            prompt = f"{self._solver_prompt}\n\n<question>\n{prompt}\n</question>"

        client = LLMClient(
            model_name=self._model_name,
            api_key=self._api_key,
            base_url=self._base_url or "https://router.huggingface.co/v1",
            system_prompt=self._system_prompt,
            temperature=self._temperature,
            enable_thinking=self._enable_thinking,
        )
        try:
            response = client.generate(prompt, max_tokens=self._max_tokens)
            content, tokens = _extract_content_and_tokens(response)
        except Exception as exc:
            elapsed = time.time() - start
            return PhysicsResult(
                task=task,
                model_answer=None,
                raw_response="",
                error=str(exc),
                tokens=None,
                elapsed_s=elapsed,
                domains=None,
            )

        model_answer = None
        error = None
        try:
            ans, unit = execute_llm_code(content)
            if ans is not None:
                model_answer = postprocess_answer({"ans": ans, "unit": unit})
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
            domains=None,
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
