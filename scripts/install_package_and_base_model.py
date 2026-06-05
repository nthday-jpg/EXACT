import os
import subprocess
import shutil
import sys

def check_dependencies():
    """Ensure pip and huggingface_hub are installed on the local machine."""
    print("Checking system dependencies...")
    
    # 1. Check and install pip in the virtual environment if it is missing (common with 'uv')
    try:
        import pip
        print("- pip is already installed.")
    except ImportError:
        print("- pip is missing in the current virtual environment.")
        if shutil.which("uv") is not None:
            print("  Detected 'uv'! Installing pip using 'uv pip install pip'...")
            subprocess.run(["uv", "pip", "install", "pip"], check=True)
            print("  pip installed successfully!")
        else:
            print("  Please ensure 'pip' is installed in your python environment manually.")
            sys.exit(1)

    # 2. Check and install huggingface_hub
    try:
        import huggingface_hub
        print("- huggingface-hub is already installed.")
    except ImportError:
        print("- huggingface-hub is missing.")
        print("  Installing huggingface-hub...")
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface-hub"], check=True)
        print("  huggingface-hub installed successfully!")

def download_packages():
    """Download required wheels compatible with Kaggle's Linux x86_64, Python 3.12 environment."""
    packages_dir = "./offline_packages"
    os.makedirs(packages_dir, exist_ok=True)
    
    print("\n" + "="*50)
    print("STEP 1: Downloading Python Packages (Wheels)")
    print("="*50)
    print("Downloading packages compatible with Kaggle's Python 3.12 & Linux environment...")
    
    # Target Python 3.12 and manylinux platform since Kaggle runs Python 3.12 on Linux x86_64
    cmd = [
        sys.executable, "-m", "pip", "download",
        "--only-binary=:all:",
        "--platform", "manylinux2014_x86_64",
        "--python-version", "3.12",
        "--implementation", "cp",
        "--abi", "cp312",
        "-d", packages_dir,
        "transformers", "trl", "peft", "datasets", "torchao"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\nAll packages downloaded successfully to ./offline_packages/")
    except subprocess.CalledProcessError as e:
        print(f"\nError occurred while downloading packages: {e}")
        print("Trying fallback download without strict target platform constraints...")
        fallback_cmd = [
            sys.executable, "-m", "pip", "download",
            "-d", packages_dir,
            "transformers", "trl", "peft", "datasets", "torchao"
        ]
        subprocess.run(fallback_cmd, check=True)
        print("\nFallback packages downloaded to ./offline_packages/")
        
    # Clean up conflicting large libraries (torch, nvidia, cuda) to use Kaggle's pre-installed optimized PyTorch/CUDA
    print("\nFiltering downloaded packages to remove large conflicting wheels (torch, nvidia, cuda)...")
    removed_count = 0
    for f in os.listdir(packages_dir):
        f_lower = f.lower()
        if (f_lower.startswith("torch") and not f_lower.startswith("torchao")) or f_lower.startswith("nvidia") or f_lower.startswith("cuda"):
            try:
                os.remove(os.path.join(packages_dir, f))
                print(f"-> Removed conflicting/large package: {f}")
                removed_count += 1
            except Exception as ex:
                print(f"-> Error removing {f}: {ex}")
    print(f"Successfully cleaned up {removed_count} conflicting wheels from ./offline_packages/.")

def download_model():
    """Download base model weights and tokenizer from Hugging Face."""
    model_dir = "./model_cache"
    os.makedirs(model_dir, exist_ok=True)
    
    print("\n" + "="*50)
    print("STEP 2: Downloading Model Weights (Qwen/Qwen3-8B)")
    print("="*50)
    
    from huggingface_hub import snapshot_download
    
    model_name = "Qwen/Qwen3-8B"
    print(f"Downloading model '{model_name}' to '{model_dir}'...")
    
    try:
        snapshot_download(
            repo_id=model_name,
            local_dir=model_dir,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],  # Save space by skipping other framework files
        )
        print(f"\nModel weights downloaded successfully to {model_dir}/")
    except Exception as e:
        print(f"\nError downloading model weights: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_dependencies()
    download_packages()
    download_model()
    
    print("\n" + "="*50)
    print("SUCCESS! NEXT STEPS:")
    print("="*50)
    print("1. Upload the raw folders 'offline_packages' and 'model_cache' as a Kaggle Dataset.")
    print("   (When creating a dataset on Kaggle, upload these two folders directly).")
    print("2. Add this dataset as an input to your Kaggle Notebook.")
    print("3. In your notebook, reference the path directly from /kaggle/input/<dataset-name>/:")
    print("   - For installing packages offline:")
    print("     !pip install --no-index --find-links=/kaggle/input/<dataset-name>/offline_packages transformers trl peft datasets torchao")
    print("   - For loading the model offline:")
    print("     MODEL_ID = '/kaggle/input/<dataset-name>/model_cache'")
    print("4. Turn Internet OFF and train with peak GPU speed offline (no unzip step needed)!"
          "\n" + "="*50 + "\n")
