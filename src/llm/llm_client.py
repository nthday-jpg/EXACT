import os
import torch
from openai import OpenAI

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LLMClient:
    def __init__(self,
                 model_name: str = "Qwen/Qwen3-8B",
                 api_key: str | None = None,
                 base_url: str = "https://router.huggingface.co/v1",
                 system_prompt: str = "",
                 temperature: float = 0.0,
                 frequency_penalty: float = 0.0,
                 use_local: bool = False,
                 model_dir: str | None = None,
                 device: str | None = None):

        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.use_local = use_local
        self.model_dir = model_dir
        self.tokenizer = None
        self.model = None

        # Resolve default model directory
        from pathlib import Path
        if not self.model_dir:
            root_dir = Path(__file__).resolve().parents[2]
            self.model_dir = str(root_dir / "results")

        # Resolve device
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")

        if not self.use_local:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
                
            self.base_url = base_url
            
            # Detect endpoint type based on the base URL
            is_modal = False
            if self.base_url and ("modal.run" in self.base_url or "modal" in self.base_url.lower()):
                is_modal = True
                
            self.api_key = api_key or os.environ.get("HF_API_KEY")
            if not self.api_key:
                if is_modal and (os.environ.get("MODAL_KEY") or os.environ.get("MODAL_SECRET")):
                    self.api_key = "modal-placeholder"
                else:
                    raise RuntimeError("HF_API_KEY is not set")
            
            headers = {}
            if is_modal:
                modal_key = os.environ.get("MODAL_KEY")
                modal_secret = os.environ.get("MODAL_SECRET")
                if modal_key:
                    headers["Modal-Key"] = modal_key
                if modal_secret:
                    headers["Modal-Secret"] = modal_secret
                
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers=headers if headers else None
            )
            
            # Load tokenizer locally to enable perfect local chat template formatting for remote completions
            from transformers import AutoTokenizer
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
            except Exception as e:
                print(f"Warning: Could not load local tokenizer for remote client: {e}")
        else:
            self.api_key = api_key or ""
            self.client = None

    def load_local_model(self) -> None:
        """Loads Hugging Face tokenizer and PEFT LoRA model locally with NF4 4-bit quantization."""
        if not self.use_local:
            return

        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        from pathlib import Path

        if not self.model_dir:
            root_dir = Path(__file__).resolve().parents[2]
            self.model_dir = str(root_dir / "results")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=(
                torch.bfloat16
                if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
                else torch.float16
            ),
            bnb_4bit_use_double_quant=True,
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-8B",
            quantization_config=bnb_config if torch.cuda.is_available() else None,
            device_map=self.device if torch.cuda.is_available() else None,
            trust_remote_code=True,
            attn_implementation="sdpa" if torch.cuda.is_available() else None,
        )

        self.model = PeftModel.from_pretrained(base_model, self.model_dir)
        self.model.eval()

    def generate(self, prompt: str, max_tokens: int | None = None, system_prompt: str | None = None) -> dict:
        """Generates text from prompt, returning a structured dictionary with token counts."""
        sys_prompt = system_prompt if system_prompt is not None else self.system_prompt
        limit_tokens = max_tokens if max_tokens is not None else 4096

        # ── Local inference ──────────────────────────────────────────────────
        if self.use_local:
            if not self.model:
                self.load_local_model()

            assert self.tokenizer is not None, "Tokenizer not loaded"
            assert self.model is not None, "Model not loaded"

            messages = []
            if sys_prompt:
                messages.append({"role": "system", "content": sys_prompt})
            messages.append({"role": "user", "content": prompt})

            chat_prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            inputs = self.tokenizer(chat_prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=limit_tokens,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id,
                )

            response_text = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
            )
            return {
                "content": response_text.strip(),
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }

        # ── Remote inference ─────────────────────────────────────────────────
        assert self.client is not None, "OpenAI client not initialised"

        messages = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        if self.tokenizer is not None:
            # Use local chat template for exact prompt formatting, then hit raw completions
            chat_prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            response = self.client.completions.create(
                model=self.model_name,
                prompt=chat_prompt,
                temperature=self.temperature,
                max_tokens=limit_tokens,
                frequency_penalty=self.frequency_penalty,
                stop=["<|im_end|>", "<|endoftext|>"],
            )

            total_tokens = response.usage.total_tokens if response.usage else 0
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            content = response.choices[0].text
            finish_reason = response.choices[0].finish_reason

        else:
            # Fallback: use chat completions endpoint
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=limit_tokens,
                frequency_penalty=self.frequency_penalty,
                stop=["<|im_end|>", "<|endoftext|>"],
            )

            total_tokens = response.usage.total_tokens if response.usage else 0
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            msg = response.choices[0].message
            content = msg.content if msg and msg.content else ""
            finish_reason = response.choices[0].finish_reason

        if finish_reason == "length" and content:
            print("Warning: Response was truncated by max_tokens.")

        if not content:
            raise RuntimeError(f"Empty content. finish_reason={finish_reason}")

        return {
            "content": content.strip(),
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    def generate_text(self, prompt: str, system_prompt: str | None = None, max_new_tokens: int = 512) -> str:
        """Helper to generate text directly as a string."""
        res = self.generate(prompt, max_tokens=max_new_tokens, system_prompt=system_prompt)
        return res["content"]