from openai import OpenAI

class LLMClient:
    def __init__(self, model_name: str, 
                 api_key: str, system_prompt: str = "", 
                 temperature: float = 0.0, extra_body: dict = {}):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.extra_body = extra_body
        self.api_key = api_key
        if not self.api_key:
            raise RuntimeError("HF_API_KEY is not set")
        self.base_url="https://router.huggingface.co/v1"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(self, prompt: str, max_tokens: int | None = None) -> dict:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens,  
            extra_body=self.extra_body,
        )
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
    
