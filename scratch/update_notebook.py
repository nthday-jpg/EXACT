import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

if not os.path.exists(notebook_path):
    print(f"Error: Notebook {notebook_path} does not exist.")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Cell 1 new source:
cell1_source = [
    "# 1. Install required packages (100% Offline Mode)\n",
    "import os\n",
    "import sys\n",
    "import subprocess\n",
    "import glob\n",
    "\n",
    "# Force Hugging Face and other libraries to run in 100% Offline Mode\n",
    "os.environ[\"HF_HUB_DISABLE_TELEMETRY\"] = \"1\"\n",
    "os.environ[\"HF_HUB_OFFLINE\"] = \"1\"\n",
    "os.environ[\"TRANSFORMERS_OFFLINE\"] = \"1\"\n",
    "\n",
    "# Exact path to the Kaggle offline packages dataset\n",
    "offline_pkg_dir = \"/kaggle/input/datasets/mduy2911/offline-packages\"\n",
    "\n",
    "# Check if wheels are nested under 'offline_packages' sub-folder\n",
    "if os.path.exists(offline_pkg_dir):\n",
    "    sub_dir = os.path.join(offline_pkg_dir, \"offline_packages\")\n",
    "    if os.path.exists(sub_dir) and len(os.listdir(sub_dir)) > 0:\n",
    "        offline_pkg_dir = sub_dir\n",
    "\n",
    "print(f\"Installing offline packages from: {offline_pkg_dir}...\")\n",
    "wheels = glob.glob(os.path.join(offline_pkg_dir, \"*.whl\")) + glob.glob(os.path.join(offline_pkg_dir, \"*.tar.gz\"))\n",
    "\n",
    "if wheels:\n",
    "    # Install all pre-cleaned wheels directly with --no-deps to bypass recursive dependency checking on torch/cuda-bindings\n",
    "    cmd = [sys.executable, \"-m\", \"pip\", \"install\", \"--no-index\", \"--no-deps\"] + wheels\n",
    "    print(f\"Installing {len(wheels)} wheels directly without dependency checks...\")\n",
    "    subprocess.run(cmd, check=True)\n",
    "    print(\"Offline installation completed successfully!\")\n",
    "else:\n",
    "    raise FileNotFoundError(f\"No offline wheels found in {offline_pkg_dir}!\")\n",
    "\n",
    "os.environ[\"CUDA_VISIBLE_DEVICES\"] = \"0\"\n",
    "os.environ[\"PYTORCH_ALLOC_CONF\"] = \"expandable_segments:True\""
]

# Cell 2 new source:
cell2_source = [
    "# 2. TRAINING HYPERPARAMETERS (Optimized for Kaggle + 96GB VRAM RTX Pro 6000)\n",
    "import os\n",
    "\n",
    "# Exact path to the Kaggle offline model cache dataset\n",
    "offline_model_dir = \"/kaggle/input/datasets/mduy2911/model-cache\"\n",
    "\n",
    "# Check if model weights are nested under 'model_cache' sub-folder\n",
    "if os.path.exists(offline_model_dir):\n",
    "    sub_dir = os.path.join(offline_model_dir, \"model_cache\")\n",
    "    if os.path.exists(sub_dir) and os.path.exists(os.path.join(sub_dir, \"config.json\")):\n",
    "        offline_model_dir = sub_dir\n",
    "\n",
    "if os.path.exists(offline_model_dir) and os.path.exists(os.path.join(offline_model_dir, \"config.json\")):\n",
    "    MODEL_ID = offline_model_dir\n",
    "    print(f\"Offline model cache detected! Loading model from: {MODEL_ID}\")\n",
    "else:\n",
    "    raise FileNotFoundError(f\"Offline model cache not found at: {offline_model_dir}\")\n",
    "\n",
    "# --- 96GB VRAM Hardware Optimizations ---\n",
    "# Setting USE_QLORA = False runs standard 16-bit LoRA (BF16) for maximum speed and stability.\n",
    "USE_QLORA = False           # Set to True only if running on limited VRAM (< 16GB) GPUs\n",
    "\n",
    "# With 96GB VRAM, we can disable gradient checkpointing entirely to gain a massive ~30% training speedup!\n",
    "GRADIENT_CHECKPOINTING = False\n",
    "\n",
    "# --- Training Hyperparameters ---\n",
    "MAX_LENGTH = 768            # Maximum sequence length\n",
    "BATCH_SIZE = 16             # Highly-optimized batch size for 96GB VRAM\n",
    "GRADIENT_ACCUMULATION = 1   # Direct gradient updates (Effective batch size = BATCH_SIZE = 16)\n",
    "EPOCHS = 1                  # Number of training epochs\n",
    "LEARNING_RATE = 2e-4        # Learning rate\n",
    "OUTPUT_DIR = \"/kaggle/working/results\"  # Output directory on Kaggle\n",
    "\n",
    "# Weights & Biases Configuration (Disabled in 100% Offline Mode)\n",
    "print(\"Running in 100% OFFLINE mode. Disabling WandB to prevent connection errors.\")\n",
    "os.environ[\"WANDB_MODE\"] = \"disabled\"\n",
    "USE_WANDB = False\n"
]

updated_cell1 = False
updated_cell2 = False
updated_cell4 = False

for cell in nb["cells"]:
    if cell["cell_type"] == "code" and len(cell["source"]) > 0:
        first_line = cell["source"][0]
        if "# 1." in first_line:
            cell["source"] = cell1_source
            updated_cell1 = True
        elif "# 2." in first_line:
            cell["source"] = cell2_source
            updated_cell2 = True
        elif "# 4." in first_line:
            new_source = []
            for line in cell["source"]:
                if "local_files_only = " in line:
                    new_source.append("local_files_only = True\n")
                    updated_cell4 = True
                else:
                    new_source.append(line)
            cell["source"] = new_source

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("="*40)
print("Notebook update status:")
print(f"Cell 1 Updated: {updated_cell1}")
print(f"Cell 2 Updated: {updated_cell2}")
print(f"Cell 4 Updated: {updated_cell4}")
print("="*40)
