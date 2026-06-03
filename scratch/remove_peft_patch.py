import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

if not os.path.exists(notebook_path):
    print("Notebook path not found")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cell4_source = [
    "# 4. Initialize Tokenizer and load Base Model (Standard 16-bit LoRA)\n",
    "import os\n",
    "import sys\n",
    "import torch\n",
    "from transformers import AutoModelForCausalLM, AutoTokenizer\n",
    "from peft import LoraConfig, get_peft_model, PeftModel\n",
    "\n",
    "device = \"cuda\" if torch.cuda.is_available() else \"cpu\"\n",
    "print(f\"Using device: {device}\")\n",
    "if torch.cuda.is_available():\n",
    "    print(f\"GPU: {torch.cuda.get_device_name(0)}\")\n",
    "\n",
    "# Check hardware bfloat16 support\n",
    "if torch.cuda.is_available() and torch.cuda.is_bf16_supported():\n",
    "    compute_dtype = torch.bfloat16\n",
    "    use_bf16 = True\n",
    "    use_fp16 = False\n",
    "    print(\"GPU supports bfloat16. Using bfloat16 compute (Optimal for Ampere/Ada/Hopper GPUs like RTX Pro 6000).\")\n",
    "else:\n",
    "    compute_dtype = torch.float16\n",
    "    use_bf16 = False\n",
    "    use_fp16 = True\n",
    "    print(\"Using float16 compute (Standard for Turing/Pascal/Volta GPUs or CPU).\")\n",
    "\n",
    "# Select the most optimal Attention implementation\n",
    "attn_impl = \"sdpa\"\n",
    "try:\n",
    "    import flash_attn\n",
    "    attn_impl = \"flash_attention_2\"\n",
    "    print(\"FlashAttention-2 is installed. Using flash_attention_2.\")\n",
    "except ImportError:\n",
    "    print(\"FlashAttention-2 not found. Using PyTorch Native SDPA (Scaled Dot Product Attention).\")\n",
    "\n",
    "# Load tokenizer and base model\n",
    "tokenizer = AutoTokenizer.from_pretrained(\n",
    "    MODEL_ID, \n",
    "    trust_remote_code=True, \n",
    "    local_files_only=True\n",
    ")\n",
    "if tokenizer.pad_token is None:\n",
    "    tokenizer.pad_token = tokenizer.eos_token\n",
    "\n",
    "print(\"Using Standard 16-bit LoRA (BF16/FP16) model loading...\")\n",
    "base_model = AutoModelForCausalLM.from_pretrained(\n",
    "    MODEL_ID,\n",
    "    dtype=compute_dtype if torch.cuda.is_available() else torch.float32,\n",
    "    device_map=\"auto\" if torch.cuda.is_available() else None,\n",
    "    trust_remote_code=True,\n",
    "    attn_implementation=attn_impl,\n",
    "    local_files_only=True\n",
    ")\n",
    "base_model.config.use_cache = False\n",
    "\n",
    "target_modules = [\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\", \"gate_proj\", \"up_proj\", \"down_proj\"]\n",
    "\n",
    "peft_config = LoraConfig(\n",
    "    r=16,\n",
    "    lora_alpha=32,\n",
    "    target_modules=target_modules,\n",
    "    lora_dropout=0.05,\n",
    "    bias=\"none\",\n",
    "    task_type=\"CAUSAL_LM\"\n",
    ")\n",
    "\n",
    "# Resume from previous checkpoints if adapter_config.json exists in OUTPUT_DIR\n",
    "adapter_config_path = os.path.join(OUTPUT_DIR, \"adapter_config.json\")\n",
    "if os.path.exists(adapter_config_path):\n",
    "    print(f\"Resuming PEFT adapter weights from {OUTPUT_DIR}...\")\n",
    "    model = PeftModel.from_pretrained(base_model, OUTPUT_DIR, is_trainable=True)\n",
    "else:\n",
    "    print(\"Initializing a new PEFT adapter...\")\n",
    "    model = get_peft_model(base_model, peft_config)\n",
    "\n",
    "model.print_trainable_parameters()\n"
]

patched = False
for cell in nb.get("cells", []):
    source = cell.get("source", [])
    if not source:
        continue
    source_str = "".join(source)
    if "# 4. Initialize Tokenizer and load Base Model" in source_str:
        cell["source"] = cell4_source
        patched = True
        break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Successfully cleaned Cell 4: removed monkey patch since torchao is updated!")
else:
    print("Could not find Cell 4 in notebook.")
