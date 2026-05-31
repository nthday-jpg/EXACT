# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  KAGGLE CELL — Upload merged model from Kaggle Dataset → HuggingFace   ║
# ║  Paste this as a new code cell in your Kaggle notebook                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# Requires Kaggle Secret: "HF_TOKEN"  (write-access token for mduy1129)
#
# Setup:
#   1. Attach dataset "mduy2911/results" to the notebook inputs
#      → model files will be at /kaggle/input/datasets/mduy2911/results/
#   2. Enable "Internet" in the notebook settings
# ---------------------------------------------------------------------------

from pathlib import Path
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login, HfApi

# ── Config ─────────────────────────────────────────────────────────────────
MODEL_DIR   = Path("/kaggle/input/datasets/mduy2911/results")   # input dataset path
REPO_ID     = "mduy1129/qwen3-8b-folc"                          # HF Hub target repo
REPO_TYPE   = "model"

# ── Auth ────────────────────────────────────────────────────────────────────
secrets  = UserSecretsClient()
hf_token = secrets.get_secret("HF_TOKEN")
login(token=hf_token, add_to_git_credential=False)
api = HfApi(token=hf_token)
print(f"✓ Authenticated as: {api.whoami()['name']}")

# ── Verify source directory ─────────────────────────────────────────────────
if not MODEL_DIR.exists():
    raise FileNotFoundError(f"Dataset not found at: {MODEL_DIR}\n"
                            "Make sure 'mduy2911/results' is attached as an input dataset.")

files = list(MODEL_DIR.iterdir())
print(f"✓ Source: {MODEL_DIR}  ({len(files)} entries)")
for f in sorted(files):
    size_mb = f.stat().st_size / 1e6 if f.is_file() else 0
    print(f"  {'[DIR]' if f.is_dir() else f'{size_mb:8.1f} MB'}  {f.name}")

# ── Ensure the HF repo exists ───────────────────────────────────────────────
print(f"\nCreating/verifying repo: {REPO_ID} …")
api.create_repo(repo_id=REPO_ID, repo_type=REPO_TYPE, exist_ok=True)
print("✓ Repository ready.")

# ── Upload ───────────────────────────────────────────────────────────────────
print(f"\nUploading model files to {REPO_ID} …")
api.upload_folder(
    folder_path=str(MODEL_DIR),
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    ignore_patterns=["checkpoint-*", "**/checkpoint-*/**"],  # skip intermediate checkpoints
    token=hf_token,
    commit_message="Upload merged Qwen3-8B-FOLC model from Kaggle dataset",
)

print(f"\n✅ Done! Model is live at: https://huggingface.co/{REPO_ID}")
