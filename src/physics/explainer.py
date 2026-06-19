from typing import Optional
from pathlib import Path
from src.llm.llm_client import LLMClient

class Explainer:
    def __init__(
        self,
        *,
        model_name: str,
        api_key: Optional[str],
        base_url: Optional[str] = None,
        system_prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = False
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key or ""
        self._base_url = base_url
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._max_tokens = max_tokens or 512
        self._enable_thinking = enable_thinking

    def explain(self, question: str, trace: dict) -> str:
        """
        Explain a physics question. Assumes the question has already been preprocessed.
        """
        template = (
            "You are a physics explainer. Your task is to explain the reasoning process behind solving physics problems.\n\n"
            "Question:\n{question}\n\n"
            "Trace:\n{trace}\n\n"
            "Please provide a detailed explanation of how to solve this problem, referencing the trace steps."
        )
        prompt = template.format(question=question, trace=trace)

        try:
            client = LLMClient(
                model_name=self._model_name,
                api_key=self._api_key,
                base_url=self._base_url or "https://router.huggingface.co/v1",
                system_prompt=self._system_prompt,
                temperature=self._temperature,
                enable_thinking=self._enable_thinking,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize LLMClient: {exc}")
        
        response = client.generate(prompt, max_tokens=self._max_tokens)
        return response.get("content", "")

def explain_physics_question(
    question: str,
    trace: dict,
    *,
    model_name: str,
    api_key: Optional[str],
    base_url: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    enable_thinking: bool = False
) -> str:
    path = Path(__file__).parent / "instructions" / "explainer.md"
    if not path.exists():
        raise FileNotFoundError(f"System prompt file not found: {path}")
    with open(path, "r") as f:
        system_prompt = f.read()
    explainer = Explainer(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        enable_thinking=enable_thinking
    )
    return explainer.explain(question, trace)