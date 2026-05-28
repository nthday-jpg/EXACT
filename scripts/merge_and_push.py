"""
merge_and_push.py

Merges the LoRA adapter (in results/) with the base model (Qwen/Qwen3-8B),
saves the merged model locally, then pushes it to HuggingFace Hub as a
full-weight model that vllm can serve.

Usage:
    uv run src/llm/tuning/merge_and_push.py
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

def main():
    # ------------------------------------------------------------------ #
    # 1. Environment & Auth
    # ------------------------------------------------------------------ #
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"

    print(f"Loading environment from: {env_path}")
    load_dotenv(dotenv_path=env_path) if env_path.exists() else load_dotenv()

    token = os.getenv("HF_API_KEY") or os.getenv("FOLC_AT")
    if not token:
        print("ERROR: Hugging Face token not found (HF_API_KEY or FOLC_AT).")
        sys.exit(1)

    # Authenticate early so HfApi calls and from_pretrained downloads work
    from huggingface_hub import login, HfApi
    login(token=token, add_to_git_credential=False)
    api = HfApi(token=token)

    try:
        username = api.whoami()["name"]
        print(f"Authenticated as HF user: {username}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 2. Paths
    # ------------------------------------------------------------------ #
    adapter_dir  = project_root / "results"          # LoRA adapter lives here
    merged_dir   = project_root / "results_merged"   # merged model goes here
    repo_id      = "mduy1129/qwen3-8b-folc"
    base_model   = "Qwen/Qwen3-8B"

    print(f"\nAdapter directory : {adapter_dir}")
    print(f"Merged output dir : {merged_dir}")
    print(f"Base model        : {base_model}")
    print(f"Target HF repo    : {repo_id}")

    if not adapter_dir.exists():
        print(f"ERROR: Adapter directory not found: {adapter_dir}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 3. Load base model + merge LoRA
    # ------------------------------------------------------------------ #
    print("\n[Step 1/3] Loading base model and LoRA adapter …")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError as e:
        print(f"ERROR: Missing dependency — {e}")
        print("Run: uv add torch transformers peft accelerate")
        sys.exit(1)

    # Load base model in float16 to keep GPU memory reasonable;
    # use CPU offload if you don't have a GPU locally.
    print(f"  Loading base model: {base_model} (bfloat16, device_map=auto) …")
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    print(f"  Loading LoRA adapter from: {adapter_dir} …")
    model = PeftModel.from_pretrained(base, str(adapter_dir))

    print("  Merging LoRA weights into base model …")
    model = model.merge_and_unload()
    print("  Merge complete.")

    # ------------------------------------------------------------------ #
    # 4. Load tokenizer (from adapter dir first, fall back to base model)
    # ------------------------------------------------------------------ #
    tokenizer_source = str(adapter_dir) if (adapter_dir / "tokenizer.json").exists() else base_model
    print(f"\n  Loading tokenizer from: {tokenizer_source}")
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source, trust_remote_code=True)

    # Copy chat template if present
    chat_template_src = adapter_dir / "chat_template.jinja"

    # ------------------------------------------------------------------ #
    # 5. Save merged model locally
    # ------------------------------------------------------------------ #
    print(f"\n[Step 2/3] Saving merged model to: {merged_dir} …")
    merged_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(merged_dir), safe_serialization=True, max_shard_size="4GB")
    tokenizer.save_pretrained(str(merged_dir))

    # Copy chat template if it exists
    if chat_template_src.exists():
        shutil.copy(chat_template_src, merged_dir / "chat_template.jinja")
        print("  Copied chat_template.jinja")

    print("  Saved successfully.")

    # ------------------------------------------------------------------ #
    # 6. Push to HuggingFace Hub
    # ------------------------------------------------------------------ #
    print(f"\n[Step 3/3] Pushing merged model to HF Hub: {repo_id} …")
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)

    api.upload_folder(
        folder_path=str(merged_dir),
        repo_id=repo_id,
        repo_type="model",
        token=token,
        # No need to exclude checkpoints — merged_dir is clean
    )

    print(f"\nSUCCESS! Merged model pushed to: https://huggingface.co/{repo_id}")
    print("You can now deploy this repo on a Hugging Face Inference Endpoint with vllm.")

if __name__ == "__main__":
    main()
