import json
import os

# Read the router system prompt
with open(r"src/physics/instructions/router.md", "r", encoding="utf-8") as f:
    router_system_prompt = f.read().strip()

# Read the original fol_and_physics notebook
with open(r"src/llm/tuning/fol_and_physics.ipynb", "r", encoding="utf-8") as f:
    notebook = json.load(f)

# Let's inspect cells in the notebook
cells = notebook["cells"]

# Update Cell 2 (hyperparameters)
# Finding the cell that defines MAX_LENGTH, BATCH_SIZE etc.
hyper_cell = None
for cell in cells:
    if cell["cell_type"] == "code" and any("MAX_LENGTH" in line for line in cell["source"]):
        hyper_cell = cell
        break

if hyper_cell:
    hyper_cell["source"] = [
        "# 2. TRAINING HYPERPARAMETERS (Optimized for RTX Pro 6000 Ada / 96GB VRAM)\n",
        "import os\n",
        "\n",
        "MODEL_ID = \"/kaggle/input/datasets/mduy2911/model-cache\"\n",
        "\n",
        "# --- RTX Pro 6000 Hardware Optimizations ---\n",
        "USE_QLORA = False\n",
        "GRADIENT_CHECKPOINTING = True\n",
        "\n",
        "# --- Training Hyperparameters ---\n",
        "MAX_LENGTH = 1500            # Maximum sequence length (optimized to cover Router prompt and response)\n",
        "BATCH_SIZE = 8            # Physical batch size optimized for RTX 6000\n",
        "GRADIENT_ACCUMULATION = 4  # Gradient accumulation steps (Effective batch size = 32)\n",
        "\n",
        "# --- 2-Phase Hyperparameters ---\n",
        "LEARNING_RATE_P1 = 1e-4      # Phase 1 learning rate (FOL focus)\n",
        "LEARNING_RATE_P2 = 5e-5      # Phase 2 learning rate (Router focus - slightly lower for fine adjustments)\n",
        "EPOCHS_P1 = 2                # Phase 1 epochs\n",
        "EPOCHS_P2 = 2                # Phase 2 epochs\n",
        "\n",
        "OUTPUT_DIR_P1 = \"/kaggle/working/results_phase1\"\n",
        "OUTPUT_DIR_P2 = \"/kaggle/working/results_phase2\"\n",
        "\n",
        "os.environ[\"WANDB_MODE\"] = \"disabled\"\n",
        "USE_WANDB = False\n"
    ]

# Update Cell 3 (data loading)
data_cell = None
for cell in cells:
    if cell["cell_type"] == "code" and any("physics_path" in line for line in cell["source"]):
        data_cell = cell
        break

if data_cell:
    # We will format the router_system_prompt as a python raw multi-line string literal
    router_prompt_escaped = router_system_prompt.replace('"""', '\\"\\"\\"')
    data_cell["source"] = [
        "# 3. Load NL -> FOL translation datasets, Router dataset, and Router Prompt\n",
        "import os\n",
        "import json\n",
        "\n",
        "merged_path = \"/kaggle/input/datasets/mduy2911/folc-train/logic_merged_valid_augmented.json\"\n",
        "router_path = \"/kaggle/input/datasets/mduy2911/folc-train/router_dataset.json\"\n",
        "\n",
        "def load_translation_dataset(path):\n",
        "    samples = []\n",
        "    seen_premises = set()\n",
        "    with open(path, \"r\", encoding=\"utf-8\") as f:\n",
        "        data = json.load(f)\n",
        "    for item in data:\n",
        "        nl_list = item.get(\"premises-NL\", [])\n",
        "        fol_list = item.get(\"premises-FOL\", [])\n",
        "        if not nl_list or not fol_list or len(nl_list) != len(fol_list):\n",
        "            continue\n",
        "        nl_serialized = \"\\n\".join(nl_list)\n",
        "        if nl_serialized in seen_premises:\n",
        "            continue\n",
        "        seen_premises.add(nl_serialized)\n",
        "        \n",
        "        sample_dict = {\n",
        "            \"premises-NL\": nl_list, \n",
        "            \"premises-FOL\": fol_list,\n",
        "            \"example_id\": item.get(\"example_id\", \"\"),\n",
        "            \"dataset_source\": item.get(\"dataset_source\", \"\"),\n",
        "            \"question\": item.get(\"question\", \"\"),\n",
        "            \"answer\": item.get(\"answer\", \"\")\n",
        "        }\n",
        "        if \"split\" in item:\n",
        "            sample_dict[\"split\"] = item[\"split\"]\n",
        "        samples.append(sample_dict)\n",
        "        \n",
        "    print(f\"Loaded {len(samples)} unique translation samples from {os.path.basename(path)}\")\n",
        "    return samples\n",
        "\n",
        "def load_router_dataset(path):\n",
        "    samples = []\n",
        "    with open(path, \"r\", encoding=\"utf-8\") as f:\n",
        "        data = json.load(f)\n",
        "    for item in data:\n",
        "        inp = item.get(\"input\", \"\")\n",
        "        out = item.get(\"output\", \"\")\n",
        "        if inp and out:\n",
        "            samples.append({\"input\": inp, \"output\": out})\n",
        "    print(f\"Loaded {len(samples)} router samples from {os.path.basename(path)}\")\n",
        "    return samples\n",
        "\n",
        "raw_samples = load_translation_dataset(merged_path)\n",
        "router_samples = load_router_dataset(router_path)\n",
        "\n",
        "router_system_prompt = \"\"\"" + router_prompt_escaped + "\"\"\".strip()\n"
    ]

# Cell 4 (model_init): Keep as is, it's generic

# Cell 5 (dataset prep):
prep_cell = None
for cell in cells:
    if cell["cell_type"] == "code" and any("train_physics" in line for line in cell["source"]):
        prep_cell = cell
        break

if prep_cell:
    prep_cell["source"] = [
        "# 5. Format Dataset (Chat Template) and split Train/Val\n",
        "import os\n",
        "import json\n",
        "import random\n",
        "from datasets import Dataset\n",
        "\n",
        "# Define prompt templates for flat JSON list output with strict count constraint\n",
        "system_prompt_template = (\n",
        "    \"You convert natural-language premises into parser-safe first-order logic formulas.\\n\\n\"\n",
        "    \"Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\\n\"\n",
        "    \"You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\\n\\n\"\n",
        "    \"ALLOWED OPERATORS:\\n\"\n",
        "    \"AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\\n\\n\"\n",
        "    \"QUANTIFIER RULES:\\n\"\n",
        "    \"Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\\n\\n\"\n",
        "    \"NUMERICAL ATTRIBUTES & COMPARISONS:\\n\"\n",
        "    \"Represent numerical attributes (e.g., age, score, GPA, duration, credits) as functions mapping to a number, and compare using operators (=, !=, >=, <=, >, <).\\n\"\n",
        "    \"E.g., \\\"John has a GPA of 3.8\\\" -> GPA(john) = 3.8\\n\"\n",
        "    \"E.g., \\\"GPA is at least 3.5\\\" -> ForAll(x, GPA(x) >= 3.5 -> ...)\\n\"\n",
        "    \"Do NOT use binary predicates like GPA(john, 3.8).\\n\\n\"\n",
        "    \"DOMAIN RESTRICTION RULE:\\n\"\n",
        "    \"Restrict the domain of quantified variables to the relevant category.\\n\"\n",
        "    \"E.g., \\\"All students are happy\\\" -> ForAll(x, Student(x) -> Happy(x))\\n\"\n",
        "    \"Do NOT write ForAll(x, Happy(x)).\\n\\n\"\n",
        "    \"Return JSON only.\"\n",
        ")\n",
        "\n",
        "user_prompt_template = (\n",
        "    \"Convert the following {num_premises} premises into canonical first-order logic.\\n\\n\"\n",
        "    \"Premises:\\n\"\n",
        "    \"{premises}\\n\\n\"\n",
        "    \"Return a JSON list of exactly {num_premises} strings containing the formulas, in the exact same order.\"\n",
        ")\n",
        "\n",
        "# --- Split FOL dataset before augmentation to prevent data leakage ---\n",
        "has_presplit = all(\"split\" in sample for sample in raw_samples)\n",
        "if has_presplit:\n",
        "    train_fol = [s for s in raw_samples if s.get(\"split\") == \"train\"]\n",
        "    val_fol = [s for s in raw_samples if s.get(\"split\") == \"val\"]\n",
        "    train_orig_fol = [s for s in train_fol if \"augmented\" not in str(s.get(\"dataset_source\", \"\"))]\n",
        "    val_orig_fol = val_fol\n",
        "    train_augmented_fol = [s for s in train_fol if \"augmented\" in str(s.get(\"dataset_source\", \"\"))]\n",
        "else:\n",
        "    original_fol = []\n",
        "    augmented_fol = []\n",
        "    for sample in raw_samples:\n",
        "        ds = str(sample.get(\"dataset_source\", \"\"))\n",
        "        if \"augmented\" in ds:\n",
        "            augmented_fol.append(sample)\n",
        "        else:\n",
        "            original_fol.append(sample)\n",
        "\n",
        "    # Shuffle original FOL samples deterministically\n",
        "    random.Random(42).shuffle(original_fol)\n",
        "    split_idx_fol = int(len(original_fol) * 0.9)\n",
        "    train_orig_fol = original_fol[:split_idx_fol]\n",
        "    val_orig_fol = original_fol[split_idx_fol:]\n",
        "\n",
        "    # Map augmented samples back to train split\n",
        "    train_orig_ids = set(x[\"example_id\"] for x in train_orig_fol)\n",
        "\n",
        "    def get_original_id(example_id):\n",
        "        for suffix in [\"_aug_var\", \"_perm_var\", \"_neg_var\"]:\n",
        "            if suffix in example_id:\n",
        "                return example_id.split(suffix)[0]\n",
        "        return example_id\n",
        "\n",
        "    train_augmented_fol = []\n",
        "    for sample in augmented_fol:\n",
        "        base_id = get_original_id(sample[\"example_id\"])\n",
        "        if base_id in train_orig_ids:\n",
        "            train_augmented_fol.append(sample)\n",
        "\n",
        "    # Combine splits\n",
        "    train_fol = train_orig_fol + train_augmented_fol\n",
        "    val_fol = val_orig_fol\n",
        "\n",
        "# --- Split Router dataset deterministically ---\n",
        "random.Random(42).shuffle(router_samples)\n",
        "split_idx_router = int(len(router_samples) * 0.9)\n",
        "train_router = router_samples[:split_idx_router]\n",
        "val_router = router_samples[split_idx_router:]\n",
        "\n",
        "# --- Format training and validation samples ---\n",
        "def format_samples(fol_list, router_list, balance_oversample=False):\n",
        "    fol_samples = []\n",
        "    # Format FOL translation samples\n",
        "    for item in fol_list:\n",
        "        nl_list = item[\"premises-NL\"]\n",
        "        fol_list_item = item[\"premises-FOL\"]\n",
        "        \n",
        "        nl_content = \"\"\n",
        "        for i, nl in enumerate(nl_list, start=1):\n",
        "            nl_content += f\"{i}. {nl}\\n\"\n",
        "            \n",
        "        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())\n",
        "        assistant_response = json.dumps(fol_list_item, indent=2)\n",
        "        \n",
        "        fol_samples.append({\n",
        "            \"messages\": [\n",
        "                {\"role\": \"system\", \"content\": system_prompt_template},\n",
        "                {\"role\": \"user\", \"content\": user_prompt.strip()},\n",
        "                {\"role\": \"assistant\", \"content\": assistant_response.strip()}\n",
        "            ]\n",
        "        })\n",
        "        \n",
        "    router_samples_formatted = []\n",
        "    # Format Router samples\n",
        "    for item in router_list:\n",
        "        router_input = item[\"input\"]\n",
        "        router_output = item[\"output\"]\n",
        "        \n",
        "        router_samples_formatted.append({\n",
        "            \"messages\": [\n",
        "                {\"role\": \"system\", \"content\": router_system_prompt},\n",
        "                {\"role\": \"user\", \"content\": f\"<QUESTION>\\n{router_input.strip()}\\n</QUESTION>\"},\n",
        "                {\"role\": \"assistant\", \"content\": router_output.strip()}\n",
        "            ]\n",
        "        })\n",
        "        \n",
        "    if balance_oversample:\n",
        "        target_len = max(len(fol_samples), len(router_samples_formatted))\n",
        "        print(f\"Balancing datasets via oversampling: target size = {target_len}\")\n",
        "        \n",
        "        if len(fol_samples) < target_len:\n",
        "            extra_needed = target_len - len(fol_samples)\n",
        "            fol_samples += random.Random(42).choices(fol_samples, k=extra_needed)\n",
        "        if len(router_samples_formatted) < target_len:\n",
        "            extra_needed = target_len - len(router_samples_formatted)\n",
        "            router_samples_formatted += random.Random(42).choices(router_samples_formatted, k=extra_needed)\n",
        "            \n",
        "    formatted = fol_samples + router_samples_formatted\n",
        "    return formatted\n",
        "\n",
        "def apply_template(batch):\n",
        "    texts = []\n",
        "    for messages in batch[\"messages\"]:\n",
        "        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)\n",
        "        texts.append(text)\n",
        "    return {\"text\": texts}\n",
        "\n",
        "# --- PREPARE VAL DATASET (Common for both phases) ---\n",
        "formatted_val = format_samples(val_fol, val_router, balance_oversample=False)\n",
        "val_dataset = Dataset.from_list(formatted_val)\n",
        "val_dataset = val_dataset.map(apply_template, batched=True, remove_columns[\"messages\"])\n",
        "val_dataset = val_dataset.shuffle(seed=42)\n",
        "\n",
        "# --- PREPARE DATASETS FOR PHASE 1 ---\n",
        "# FOL: 100%, Router: 20%\n",
        "num_router_p1 = int(len(train_router) * 0.20)\n",
        "train_router_p1 = train_router[:num_router_p1]\n",
        "\n",
        "formatted_train_p1 = format_samples(train_fol, train_router_p1, balance_oversample=False)\n",
        "train_dataset_p1 = Dataset.from_list(formatted_train_p1)\n",
        "train_dataset_p1 = train_dataset_p1.map(apply_template, batched=True, remove_columns[\"messages\"])\n",
        "train_dataset_p1 = train_dataset_p1.shuffle(seed=42)\n",
        "\n",
        "# --- PREPARE DATASETS FOR PHASE 2 ---\n",
        "# Router: 100%, FOL: 50%\n",
        "num_fol_p2 = int(len(train_fol) * 0.50)\n",
        "train_fol_p2 = random.Random(42).sample(train_fol, num_fol_p2)\n",
        "\n",
        "formatted_train_p2 = format_samples(train_fol_p2, train_router, balance_oversample=False)\n",
        "train_dataset_p2 = Dataset.from_list(formatted_train_p2)\n",
        "train_dataset_p2 = train_dataset_p2.map(apply_template, batched=True, remove_columns[\"messages\"])\n",
        "train_dataset_p2 = train_dataset_p2.shuffle(seed=42)\n",
        "\n",
        "print(f\"FOL Train/Val Split: original train={len(train_orig_fol)}, original val={len(val_orig_fol)}\")\n",
        "print(f\"FOL Augmented added to Train: {len(train_augmented_fol)}\")\n",
        "print(f\"Router Train/Val Split: train={len(train_router)}, val={len(val_router)}\")\n",
        "print(f\"Common Validation size: {len(val_dataset)}\")\n",
        "print(f\"Phase 1 - Train size (100% FOL : 20% Router): {len(train_dataset_p1)}\")\n",
        "print(f\"Phase 2 - Train size (100% Router : 50% FOL): {len(train_dataset_p2)}\")\n"
    ]

# Cell 6 (training_sft / custom loss & evaluation for router):
# Replace evaluate_physics_accuracy definition and custom trainer call
train_cell = None
for cell in cells:
    if cell["cell_type"] == "code" and any("def evaluate_physics_accuracy" in line for line in cell["source"]):
        train_cell = cell
        break

if train_cell:
    # Let's inspect its code and write a replacement that contains:
    # 1. clean_json_response
    # 2. FOL prover / evaluator
    # 3. Router evaluator (evaluate_router_accuracy)
    # 4. CustomSFTTrainer
    # 5. train_model (running evaluate_router_accuracy at the end)
    
    # We will build train_cell["source"] programmatically
    # Let's import Z3 symbols and parser code, and the new evaluate_router_accuracy function
    # Note: evaluate_router_accuracy checks valid_json, exact domains list match, multi_state boolean match, and overall exact match
    
    # Let's extract the parts of the original train_cell source that are logic-related (lines 454 to 1639 of fol_and_physics.ipynb)
    # We can fetch them or just rebuild the whole code cleanly.
    # To keep it exact, we can rebuild the cell contents with evaluate_router_accuracy.
    
    # Let's load the logic evaluation parts directly from the existing cell in fol_and_physics.ipynb
    # and replace evaluate_physics_accuracy with evaluate_router_accuracy.
    
    # Let's read lines of Cell 6 from the original notebook to avoid any missing helper functions.
    # We did view the whole of Cell 6 in fol_and_physics.ipynb earlier!
    # Let's check lines 498 to 1878.
    # We will build the new code block for Cell 6.
    pass

# We will let a helper python code do the parsing and building.
print("Generator script generated successfully.")
