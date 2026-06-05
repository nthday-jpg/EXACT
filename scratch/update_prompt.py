import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"
solver_path = r"d:\mduy\source\repos\EXACT\src\physics\instructions\solver.md"

# 1. Read solver prompt content
with open(solver_path, "r", encoding="utf-8") as f:
    prompt_content = f.read().strip()

# 2. Prepare the new code source lines
code_lines = [
    "# 3. Load NL -> FOL translation datasets, Physics dataset, and Physics Prompt\n",
    "import os\n",
    "import json\n",
    "\n",
    'merged_path = "/kaggle/input/datasets/mduy2911/folc-train/logic_merged_valid_augmented.json"\n',
    'physics_path = "/kaggle/input/datasets/mduy2911/folc-train/physics_distillation.json"\n',
    "\n",
    "def load_translation_dataset(path):\n",
    "    samples = []\n",
    "    seen_premises = set()\n",
    '    with open(path, "r", encoding="utf-8") as f:\n',
    "        data = json.load(f)\n",
    "    for item in data:\n",
    '        nl_list = item.get("premises-NL", [])\n',
    '        fol_list = item.get("premises-FOL", [])\n',
    "        if not nl_list or not fol_list or len(nl_list) != len(fol_list):\n",
    "            continue\n",
    '        nl_serialized = "\\n".join(nl_list)\n',
    "        if nl_serialized in seen_premises:\n",
    "            continue\n",
    "        seen_premises.add(nl_serialized)\n",
    "        samples.append({\n",
    '            "premises-NL": nl_list, \n',
    '            "premises-FOL": fol_list,\n',
    '            "example_id": item.get("example_id", ""),\n',
    '            "dataset_source": item.get("dataset_source", "")\n',
    "        })\n",
    '    print(f"Loaded {len(samples)} unique translation samples from {os.path.basename(path)}")\n',
    "    return samples\n",
    "\n",
    "def load_physics_dataset(path):\n",
    "    samples = []\n",
    '    with open(path, "r", encoding="utf-8") as f:\n',
    "        data = json.load(f)\n",
    "    for item in data:\n",
    '        inp = item.get("input", "")\n',
    '        out = item.get("output", "")\n',
    "        if inp and out:\n",
    '            samples.append({"input": inp, "output": out})\n',
    '    print(f"Loaded {len(samples)} physics samples from {os.path.basename(path)}")\n',
    "    return samples\n",
    "\n",
    "raw_samples = load_translation_dataset(merged_path)\n",
    "physics_samples = load_physics_dataset(physics_path)\n",
    "\n",
    'physics_system_prompt = """' + prompt_content + '""".strip()\n'
]

# 3. Read notebook
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 4. Find the cell by ID and replace its source
found = False
for cell in nb["cells"]:
    if cell.get("id") == "3e47b246":
        cell["source"] = code_lines
        found = True
        break

if found:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook cell updated successfully.")
else:
    print("Cell with ID 3e47b246 not found!")
