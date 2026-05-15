from openai import OpenAI

class LLMClient:
    def __init__(self, model_name: str, api_key: str, system_prompt: str = "", temperature: float = 0.0):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.api_key = api_key
        if not self.api_key:
            raise RuntimeError("HF_API_KEY is not set")
        self.base_url="https://router.huggingface.co/v1"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(self, prompt: str):
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature
        )
        msg = response.choices[0].message
        content = msg.content if msg and msg.content else ""
        if not content:
            raise RuntimeError(f"Empty content. finish_reason={response.choices[0].finish_reason}")
        return content.strip()
    
