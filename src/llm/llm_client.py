import os
import torch
from openai import OpenAI

class LLMClient:
    def __init__(self, 
                 model_name: str = "Qwen/Qwen3-8B", 
                 api_key: str = None, 
                 base_url: str = "https://router.huggingface.co/v1",
                 system_prompt: str = "", 
                 temperature: float = 0.0, 
                 extra_body: dict = {},
                 use_local: bool = False,
                 model_dir: str = None):
        
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.extra_body = extra_body
        self.use_local = use_local
        self.model_dir = model_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.tokenizer = None
        self.model = None
        
        if not self.use_local:
            self.api_key = api_key or os.environ.get("HF_API_KEY")
            if not self.api_key:
                raise RuntimeError("HF_API_KEY is not set")
            self.base_url = base_url
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.api_key = api_key
            self.client = None

    def load_local_model(self):
        """Loads Hugging Face tokenizer and PEFT LoRA model locally with NF4 4-bit quantization."""
        if not self.use_local:
            return
            
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        from pathlib import Path
        
        # Resolve default model directory if none provided
        if not self.model_dir:
            # llm_client.py is at src/llm/llm_client.py, so parents[2] is the project root (EXACT/)
            root_dir = Path(__file__).resolve().parents[2]
            self.model_dir = str(root_dir / "results")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-8B",
            quantization_config=bnb_config if torch.cuda.is_available() else None,
            device_map="cuda:0" if torch.cuda.is_available() else None,
            trust_remote_code=True,
            attn_implementation="sdpa" if torch.cuda.is_available() else None
        )
        
        self.model = PeftModel.from_pretrained(base_model, self.model_dir)
        self.model.eval()

    def generate(self, prompt: str, max_tokens: int | None = None, system_prompt: str | None = None) -> dict:
        """Generates text from prompt, returning a structured dictionary with token counts."""
        sys_prompt = system_prompt if system_prompt is not None else self.system_prompt
        
        if self.use_local:
            if not self.model:
                self.load_local_model()
                
            messages = []
            if sys_prompt:
                messages.append({"role": "system", "content": sys_prompt})
            messages.append({"role": "user", "content": prompt})
            
            chat_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            inputs = self.tokenizer(chat_prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens if max_tokens is not None else 512,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id
                )
                
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            content = response.strip()
            
            return {
                "content": content,
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0
            }
        else:
            messages = []
            if sys_prompt:
                messages.append({"role": "system", "content": sys_prompt})
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
            content = msg.content if msg and msg.content else ""
            if not content and hasattr(msg, 'reasoning') and msg.reasoning:
                content = msg.reasoning
            
            if response.choices[0].finish_reason == "length" and content:
                print("Warning: Response was truncated by max_tokens.")
                return {"content": content.strip(), "total_tokens": total_tokens, "input_tokens": input_tokens, "output_tokens": output_tokens}
                
            if not content:
                raise RuntimeError(f"Empty content. finish_reason={response.choices[0].finish_reason}")
                
            return {"content": content.strip(),
                    "total_tokens": total_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens}

    def generate_text(self, prompt: str, system_prompt: str | None = None, max_new_tokens: int = 512) -> str:
        """Helper to generate text directly as a string."""
        res = self.generate(prompt, max_tokens=max_new_tokens, system_prompt=system_prompt)
        return res["content"]
