import os
import modal

app = modal.App("exact-qwen3-8b-lora")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "transformers>=4.40.0",
        "peft>=0.11.0",
        "torch",
        "huggingface_hub",
        "accelerate",
        "fastapi",
        "uvicorn",
        "pydantic"
    )
    .add_local_dir("d:/mduy/source/repos/EXACT/results_physics", remote_path="/adapters/physics")
    .add_local_dir("d:/mduy/source/repos/EXACT/results_fol_and_router", remote_path="/adapters/fol_router")
)

@app.cls(
    image=image,
    gpu="L4",
    cpu=4,
    memory=32768,       # 32 GB system RAM to ensure fast loading
    timeout=600,
    scaledown_window=120, # Shut down after 2 minutes of inactivity to save cost
    secrets=[modal.Secret.from_dotenv()],
)
class ExactModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        
        # Load Hugging Face token from environment if present
        token = os.environ.get("HF_TOKEN") or os.environ.get("HF_API_KEY") or os.environ.get("FOLC_AT")
        if token:
            print("HF token detected. Passing to tokenizer and model downloaders.")
        
        print("Loading tokenizer for Qwen/Qwen3-8B...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen3-8B", 
            trust_remote_code=True,
            token=token
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        print("Loading base model: Qwen/Qwen3-8B...")
        base = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-8B",
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            token=token
        )
        
        print("Loading physics adapter...")
        self.model = PeftModel.from_pretrained(base, "/adapters/physics", adapter_name="physics")
        print("Loading fol_router adapter...")
        self.model.load_adapter("/adapters/fol_router", adapter_name="fol_router")
        self.model.eval()
        print("Model and adapters loaded successfully!")

    @modal.asgi_app()
    def api_server(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList
        
        # Define stopping criteria for Hugging Face generate to stop at stop sequences
        class StopSequenceCriteria(StoppingCriteria):
            def __init__(self, stop_sequences, tokenizer):
                self.stop_ids = [tokenizer.encode(seq, add_special_tokens=False) for seq in stop_sequences]
                
            def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
                for stop_seq in self.stop_ids:
                    if len(stop_seq) == 0:
                        continue
                    if input_ids.shape[1] >= len(stop_seq):
                        last_tokens = input_ids[0, -len(stop_seq):].tolist()
                        if last_tokens == stop_seq:
                            return True
                return False

        web_app = FastAPI(title="EXACT Dynamic Adapter Server")
        
        @web_app.get("/v1/models")
        async def get_models():
            return {
                "object": "list",
                "data": [
                    {"id": "physics", "object": "model", "created": 1700000000, "owned_by": "exact"},
                    {"id": "fol_router", "object": "model", "created": 1700000000, "owned_by": "exact"}
                ]
            }

        @web_app.post("/v1/chat/completions")
        async def chat_completions(request: Request):
            data = await request.json()
            model_name = data.get("model", "fol_router")
            messages = data.get("messages", [])
            temperature = data.get("temperature", 0.0)
            max_tokens = data.get("max_tokens", 512)
            stop_words = data.get("stop", ["<|im_end|>", "<|endoftext|>"])
            if isinstance(stop_words, str):
                stop_words = [stop_words]
                
            # Set adapter dynamically
            adapter_to_use = "physics" if "physics" in model_name else "fol_router"
            print(f"Setting active adapter to: {adapter_to_use}")
            self.model.set_adapter(adapter_to_use)
            
            # Format using tokenizer's apply_chat_template
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
            
            stopping_criteria = StoppingCriteriaList([StopSequenceCriteria(stop_words, self.tokenizer)]) if stop_words else None
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature if temperature > 0.0 else None,
                    do_sample=temperature > 0.0,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id,
                    stopping_criteria=stopping_criteria,
                )
                
            # Decode generated tokens only
            input_len = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_len:]
            response_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # Construct standard OpenAI response
            import time
            resp_id = f"chatcmpl-{int(time.time())}"
            
            return {
                "id": resp_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": input_len,
                    "completion_tokens": len(generated_tokens),
                    "total_tokens": input_len + len(generated_tokens)
                }
            }

        @web_app.post("/v1/completions")
        async def completions(request: Request):
            data = await request.json()
            model_name = data.get("model", "fol_router")
            prompt = data.get("prompt", "")
            temperature = data.get("temperature", 0.0)
            max_tokens = data.get("max_tokens", 512)
            stop_words = data.get("stop", ["<|im_end|>", "<|endoftext|>"])
            if isinstance(stop_words, str):
                stop_words = [stop_words]
                
            # Set adapter dynamically
            adapter_to_use = "physics" if "physics" in model_name else "fol_router"
            print(f"Setting active adapter to: {adapter_to_use}")
            self.model.set_adapter(adapter_to_use)
            
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
            
            stopping_criteria = StoppingCriteriaList([StopSequenceCriteria(stop_words, self.tokenizer)]) if stop_words else None
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature if temperature > 0.0 else None,
                    do_sample=temperature > 0.0,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id,
                    stopping_criteria=stopping_criteria,
                )
                
            # Decode generated tokens only
            input_len = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_len:]
            response_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # Construct standard OpenAI response
            import time
            resp_id = f"cmpl-{int(time.time())}"
            
            return {
                "id": resp_id,
                "object": "text_completion",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "text": response_text,
                        "index": 0,
                        "logprobs": None,
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": input_len,
                    "completion_tokens": len(generated_tokens),
                    "total_tokens": input_len + len(generated_tokens)
                }
            }

        return web_app
