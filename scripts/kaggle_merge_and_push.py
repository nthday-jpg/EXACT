# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  KAGGLE CELL — Merge LoRA adapter → full model & push to HuggingFace   ║
# ║  Paste this as a new code cell in train_folc_kaggle.ipynb               ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# Requires Kaggle Secret: "HF_TOKEN"  (write-access token for mduy1129 org)
#
# Setup:
#   1. Add dataset "mduy2911/qwen3-8b-folc-adapter" to the notebook inputs
#      → adapter will be at /kaggle/input/qwen3-8b-folc-adapter/
#   2. If dataset not attached, falls back to pulling adapter from HF Hub.
#
# Run on a GPU accelerator (P100/T4/L4/A100) — needs ~25 GB VRAM.
# ---------------------------------------------------------------------------

import gc
import torch
from pathlib import Path
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login, HfApi
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ── Config ─────────────────────────────────────────────────────────────────
BASE_MODEL_ID = "Qwen/Qwen3-8B"
MERGED_REPO   = "mduy1129/qwen3-8b-folc"     # push merged model here
MERGED_DIR    = Path("/kaggle/working/merged")

# Adapter source: prefer local Kaggle dataset (mduy2911/results), fall back to HF Hub
LOCAL_ADAPTER  = Path("/kaggle/input/datasets/mduy2911/results")  # mduy2911/results dataset
if not LOCAL_ADAPTER.exists():
    # fallback: old dataset slug path Kaggle sometimes uses
    LOCAL_ADAPTER = Path("/kaggle/input/results")
ADAPTER_SOURCE = str(LOCAL_ADAPTER) if LOCAL_ADAPTER.exists() else "mduy1129/qwen3-8b-folc"
print(f"Adapter source: {'LOCAL → ' + str(LOCAL_ADAPTER) if LOCAL_ADAPTER.exists() else 'HF Hub → ' + ADAPTER_SOURCE}")

# ── Auth ────────────────────────────────────────────────────────────────────
secrets  = UserSecretsClient()
hf_token = secrets.get_secret("HF_TOKEN")
login(token=hf_token, add_to_git_credential=False)
api = HfApi(token=hf_token)
print(f"Authenticated as: {api.whoami()['name']}")

# ── Free GPU memory left over from training ─────────────────────────────────
for _var in ["trainer", "model", "base_model", "peft_model", "merged"]:
    if _var in globals():
        del globals()[_var]
gc.collect()
torch.cuda.empty_cache()
print(f"GPU memory reserved after cleanup: {torch.cuda.memory_reserved(0)/1e9:.1f} GB")

# ── Load base model in bfloat16 (NO quantization — merge needs full weights) ─
print(f"\n[1/4] Loading base model: {BASE_MODEL_ID} …")
base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_ID,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

# ── Attach LoRA adapter (local Kaggle dataset or HF Hub) ────────────────────
print(f"[2/4] Loading LoRA adapter from: {ADAPTER_SOURCE} …")
peft_model = PeftModel.from_pretrained(
    base,
    ADAPTER_SOURCE,
    token=hf_token if not LOCAL_ADAPTER.exists() else None,
)

# ── Merge adapter weights into base model ───────────────────────────────────
print("[3/4] Merging LoRA weights (merge_and_unload) …")
merged = peft_model.merge_and_unload()
del peft_model, base
gc.collect()
torch.cuda.empty_cache()
print("      Merge complete.")

# ── Load tokenizer (from local dataset if available) ─────────────────────────
print(f"      Loading tokenizer from: {ADAPTER_SOURCE} …")
tokenizer = AutoTokenizer.from_pretrained(
    ADAPTER_SOURCE,
    token=hf_token if not LOCAL_ADAPTER.exists() else None,
    trust_remote_code=True,
)

# ── Save merged model locally ────────────────────────────────────────────────
print(f"[4/4] Saving merged model to {MERGED_DIR} …")
MERGED_DIR.mkdir(parents=True, exist_ok=True)
merged.save_pretrained(str(MERGED_DIR), safe_serialization=True, max_shard_size="4GB")
tokenizer.save_pretrained(str(MERGED_DIR))
print("      Saved.")

# ── Push to HuggingFace Hub ───────────────────────────────────────────────────
print(f"\nPushing to HF Hub: {MERGED_REPO} …")
api.create_repo(repo_id=MERGED_REPO, repo_type="model", exist_ok=True)
api.upload_folder(
    folder_path=str(MERGED_DIR),
    repo_id=MERGED_REPO,
    repo_type="model",
    token=hf_token,
)

print(f"\n✅ Done! Merged model live at: https://huggingface.co/{MERGED_REPO}")
print("   Restart the HF Inference Endpoint — vllm will find config.json and serve it.")
