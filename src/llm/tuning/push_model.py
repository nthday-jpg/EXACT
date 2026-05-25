import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi, login

def main():
    # 1. Load environment variables from .env
    # Find project root where .env is located
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    
    print(f"Loading environment from: {env_path}")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
        
    # Get Hugging Face token
    # HF_API_KEY belongs to mduy1129, FOLC_AT belongs to nthday-jpg
    token = os.getenv("HF_API_KEY") or os.getenv("FOLC_AT")
    
    if not token:
        print("ERROR: Hugging Face token not found in environment variables (HF_API_KEY or FOLC_AT).")
        sys.exit(1)
        
    api = HfApi(token=token)
    
    try:
        user_info = api.whoami()
        username = user_info.get("name")
        print(f"Authenticated successfully as HF user: {username}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)
        
    repo_id = "mduy1129/qwen3-8b-folc"
    results_dir = project_root / "results"
    
    if not results_dir.exists():
        print(f"ERROR: Results directory does not exist at: {results_dir}")
        sys.exit(1)
        
    print(f"Model source directory: {results_dir}")
    print(f"Target repository ID: {repo_id}")
    
    # 2. Ensure the repository exists
    print(f"Creating/verifying Hugging Face repository: {repo_id}...")
    try:
        api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
        print("Repository is ready.")
    except Exception as e:
        print(f"Failed to create/verify repository: {e}")
        print("Will attempt to upload directly (in case repository already exists and we have access).")

    # 3. Upload model files, excluding intermediate checkpoints
    print("Uploading folder contents to Hugging Face Hub (excluding 'checkpoint-*' folders)...")
    try:
        # ignore_patterns ignores intermediate checkpoints
        api.upload_folder(
            folder_path=str(results_dir),
            repo_id=repo_id,
            repo_type="model",
            ignore_patterns=["checkpoint-*", "**/checkpoint-*/**"],
            token=token
        )
        print("\nSUCCESS: Model files uploaded successfully!")
        print(f"You can view your model repository here: https://huggingface.co/{repo_id}")
    except Exception as e:
        print(f"\nERROR occurred during upload: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
