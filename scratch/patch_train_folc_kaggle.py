import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

if not os.path.exists(notebook_path):
    print(f"Error: Notebook not found at {notebook_path}")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

patched = False
for idx, cell in enumerate(nb.get("cells", [])):
    source = cell.get("source", [])
    if not source:
        continue
        
    source_str = "".join(source)
    if "# 4. Initialize Tokenizer and load Base Model" in source_str:
        print(f"Patching cell 4 in notebook at index {idx}...")
        
        new_source = [
            "# 4. Initialize Tokenizer and load Base Model (Supports 16-bit LoRA and 4-bit QLoRA)\n",
            "import sys\n",
            "import torch\n",
            "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n",
            "\n",
            "# Unconditionally patch PEFT's torchao detection to prevent incompatible version crashes\n",
            "try:\n",
            "    import peft\n",
            "    import peft.import_utils\n",
            "    peft.import_utils.is_torchao_available = lambda *args, **kwargs: False\n",
            "    for name, module in list(sys.modules.items()):\n",
            "        if name.startswith(\"peft\"):\n",
            "            if hasattr(module, \"is_torchao_available\"):\n",
            "                setattr(module, \"is_torchao_available\", lambda *args, **kwargs: False)\n",
            "    print(\"Successfully patched PEFT to bypass incompatible torchao version check.\")\n",
            "except Exception as e:\n",
            "    print(f\"Warning: Failed to patch PEFT torchao detection: {e}\")\n",
            "\n",
            "# Mock bitsandbytes to bypass any potential bitsandbytes import/setup crashes when not using QLoRA\n",
            "if not USE_QLORA:\n",
            "    from types import ModuleType\n",
            "    class DummyType(type):\n",
            "        def __getattr__(cls, name):\n",
            "            return DummyType(name, (object,), {})\n",
            "    class DummyClass(metaclass=DummyType):\n",
            "        pass\n",
            "    class BnbMockFinder:\n",
            "        def find_spec(self, fullname, path, target=None):\n",
            "            if fullname == \"bitsandbytes\" or fullname.startswith(\"bitsandbytes.\"):\n",
            "                from importlib.machinery import ModuleSpec\n",
            "                return ModuleSpec(fullname, self)\n",
            "            return None\n",
            "        def create_module(self, spec):\n",
            "            return DummyClass\n",
            "        def exec_module(self, module):\n",
            "            pass\n",
            "    sys.meta_path.insert(0, BnbMockFinder())\n",
            "    sys.modules[\"bitsandbytes\"] = DummyClass\n",
            "    sys.modules[\"bitsandbytes.nn\"] = DummyClass\n",
            "    sys.modules[\"bitsandbytes.optim\"] = DummyClass\n",
            "    print(\"Successfully registered bitsandbytes mock to prevent setup crashes during 16-bit LoRA training.\")\n",
            "\n",
            "from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel\n",
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
            "# Determine if we should load strictly from local files\n",
            "local_files_only = True\n",
            "print(f\"Loading model and tokenizer with local_files_only={local_files_only}\")\n",
            "\n",
            "# Load tokenizer\n",
            "tokenizer = AutoTokenizer.from_pretrained(\n",
            "    MODEL_ID, \n",
            "    trust_remote_code=True, \n",
            "    local_files_only=local_files_only\n",
            ")\n",
            "if tokenizer.pad_token is None:\n",
            "    tokenizer.pad_token = tokenizer.eos_token\n",
            "\n",
            "# Load Model\n",
            "if torch.cuda.is_available() and USE_QLORA:\n",
            "    print(\"Using 4-bit QLoRA Quantization for model loading...\")\n",
            "    bnb_config = BitsAndBytesConfig(\n",
            "        load_in_4bit=True,\n",
            "        bnb_4bit_quant_type=\"nf4\",\n",
            "        bnb_4bit_compute_dtype=compute_dtype,\n",
            "        bnb_4bit_use_double_quant=True\n",
            "    )\n",
            "    base_model = AutoModelForCausalLM.from_pretrained(\n",
            "        MODEL_ID,\n",
            "        quantization_config=bnb_config,\n",
            "        device_map=\"auto\",\n",
            "        trust_remote_code=True,\n",
            "        attn_implementation=attn_impl,\n",
            "        local_files_only=local_files_only\n",
            "    )\n",
            "    base_model.config.use_cache = False\n",
            "    base_model = prepare_model_for_kbit_training(base_model)\n",
            "else:\n",
            "    print(\"Using Standard 16-bit LoRA (BF16/FP16) model loading...\")\n",
            "    base_model = AutoModelForCausalLM.from_pretrained(\n",
            "        MODEL_ID,\n",
            "        torch_dtype=compute_dtype if torch.cuda.is_available() else torch.float32,\n",
            "        device_map=\"auto\" if torch.cuda.is_available() else None,\n",
            "        trust_remote_code=True,\n",
            "        attn_implementation=attn_impl,\n",
            "        local_files_only=local_files_only\n",
            "    )\n",
            "    base_model.config.use_cache = False\n",
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
        
        cell["source"] = new_source
        patched = True
        break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook updated successfully!")
else:
    print("Could not find cell 4 in notebook.")
