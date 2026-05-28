"""
Modal Labs deployment: Fine-tuned Qwen3-8B Merged model served via high-performance vLLM.
Compatible with Modal v1.x (>=1.0).

This version replaces the slow, sequential Hugging Face Transformers backend with vLLM,
enabling Continuous Batching and PagedAttention to maximize GPU utilization and cut costs.
By using the merged weights repository, we avoid LoRA assertion errors on custom architectures.

Usage:
  1. Deploy:                modal deploy modal_serve.py
     (or dev mode)          modal serve modal_serve.py

The endpoint URL will be printed after deploy. Use it in evaluate_200_samples.py via:
  uv run ./tests/evaluate_200_samples.py --modal-url <printed-URL>
"""

import os
import modal

# ---------------------------------------------------------------------------
# Modal app & resources
# ---------------------------------------------------------------------------
app = modal.App("exact-qwen3-8b-lora")

BASE_MODEL_ID   = "mduy1129/qwen3-8b-folc"
MODEL_NAME      = "exact-qwen3-8b"

# ---------------------------------------------------------------------------
# Container image with vLLM
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "vllm==0.7.3",
        "transformers<5.0.0",
        "huggingface_hub>=0.30.0",
        "peft>=0.19.1",
    )
)

# ---------------------------------------------------------------------------
# vLLM Serving Class
# ---------------------------------------------------------------------------
@app.cls(
    image=image,
    gpu="L4",
    cpu=4,              # 4 physical cores
    memory=16384,       # 16 GB system RAM
    timeout=600,
    scaledown_window=120, # Shut down after 2 minutes of inactivity to save money
    secrets=[modal.Secret.from_dotenv()], # Unconditionally load local secrets (.env) for HF authentication
)
class ExactModel:
    @modal.web_server(port=8000, startup_timeout=300)
    def api_server(self):
        import subprocess

        # Construct vLLM serve command
        cmd = [
            "vllm", "serve", BASE_MODEL_ID,
            "--port", "8000",
            "--host", "0.0.0.0",
            "--served-model-name", MODEL_NAME,
            "--max-model-len", "8192",  # Support up to 8192 token context
            "--gpu-memory-utilization", "0.90", # Allocate 90% of L4 memory to vLLM
        ]

        # Pass Hugging Face token if available in env to download private repository
        env = os.environ.copy()
        hf_token = env.get("HF_TOKEN") or env.get("HF_API_KEY") or env.get("FOLC_AT")
        if hf_token:
            env["HF_TOKEN"] = hf_token
            print("vLLM: Hugging Face token detected and set in container environment.")

        print(f"Starting vLLM server: {' '.join(cmd)}")
        return subprocess.Popen(cmd, env=env)
