from openai import OpenAI
from typing import Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class LLMClient:
    def __init__(self, model_name: str, 
                 api_key: str, base_url: str = "https://router.huggingface.co/v1",
                 system_prompt: str = "", 
                 temperature: float = 0.0,
                 enable_thinking: bool = False,
        ):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.enable_thinking = enable_thinking
        self.api_key = api_key or "sk-dummy" 
        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(self, prompt: str, max_tokens: int | None = None) -> dict:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        create_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "frequency_penalty": 0.0,
            "seed": 42,
        }
        if self.enable_thinking:
            extra_body: dict[str, Any] = {"chat_template_kwargs": {"enable_thinking": True}}
            create_kwargs["extra_body"] = extra_body

        response = self.client.chat.completions.create(**create_kwargs)
        total_tokens = response.usage.total_tokens
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        msg = response.choices[0].message
        
        # Guard against truncated/incomplete text safely
        content = msg.content if msg and msg.content else ""
        
        # If it cut off due to length, we might still have partial text we can use
        if response.choices[0].finish_reason == "length" and content:
            print("Warning: Response was truncated by max_tokens.")
            return {"content": content.strip(), "total_tokens": total_tokens, "input_tokens": input_tokens, "output_tokens": output_tokens}
            
        if not content:
            raise RuntimeError(f"Empty content. finish_reason={response.choices[0].finish_reason}")
            
        return {"content": content.strip(),
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens}
    
