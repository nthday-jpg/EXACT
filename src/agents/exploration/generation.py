from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from tqdm import tqdm

from src.llm.llm_client import LLMClient


def generate_heuristics_with_llm(
	*,
	failures: List[dict],
	model_name: str,
	api_key: Optional[str],
	system_prompt: str,
	base_url: str = "https://router.huggingface.co/v1",
	chunk_size: int = 25,
	temperature: float = 0.1,
	enable_thinking: bool = False,
	verbose: bool = False,
) -> str:
	if not failures:
		return "# Heuristics From Failures\n\nNo failures to summarize.\n"

	client = LLMClient(
		model_name=model_name,
		api_key=api_key or "",
		base_url=base_url,
		system_prompt=system_prompt,
		temperature=temperature,
		enable_thinking=enable_thinking,
	)

	chunks = list(_chunked(failures, max(1, chunk_size)))
	outputs: List[str] = []
	iterator = tqdm(enumerate(chunks, start=1), total=len(chunks), desc="Generating heuristics", disable=not verbose)
	for idx, chunk in iterator:
		prompt = _build_prompt(chunk, idx, len(chunks))
		response = client.generate(prompt)
		content = response.get("content") if isinstance(response, dict) else str(response)
		outputs.append(str(content).strip())

	return "\n\n".join(outputs).strip() + "\n"


def _chunked(items: Iterable[dict], size: int) -> Iterable[List[dict]]:
	batch: List[dict] = []
	for item in items:
		batch.append(item)
		if len(batch) >= size:
			yield batch
			batch = []
	if batch:
		yield batch


def _build_prompt(chunk: List[dict], index: int, total: int) -> str:
	payload = {
		"chunk_index": index,
		"total_chunks": total,
		"failures": [_format_failure(item) for item in chunk],
	}

	return (
		"Summarize common failure patterns and propose concise heuristics. "
		"Return markdown with short bullet points.\n\n"
		+ json.dumps(payload, ensure_ascii=True)
	)


def _format_failure(failure: dict) -> Dict[str, Any]:
	return {
		"question": failure.get("question"),
		"correct": failure.get("correct"),
		"model_answer": failure.get("model_answer"),
		"raw_response": failure.get("raw_response"),
		"error": failure.get("error"),
	}
