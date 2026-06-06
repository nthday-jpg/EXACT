import json

ipynb_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\folc.ipynb"

with open(ipynb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find the cell containing "def load_translation_dataset"
target_cell = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "def load_translation_dataset" in source:
            target_cell = cell
            break

if target_cell is None:
    print("Could not find the target loading cell in notebook.")
    exit(1)

# New source code for the cell
new_source = [
    "# 3. Load NL -> FOL Translation Datasets (Paths left blank per user request)\n",
    "import os\n",
    "import json\n",
    "\n",
    "merged_path = \"/kaggle/input/datasets/mduy2911/folc-train/logic_merged_valid_augmented.json\"\n",
    "no_aug_path = \"/kaggle/input/datasets/mduy2911/folc-train/logic_merged_valid.json\" \n",
    "\n",
    "def load_translation_dataset(path):\n",
    "    if not path or not os.path.exists(path):\n",
    "        print(f\"Warning: Path '{path}' is empty or does not exist. Skipping load.\")\n",
    "        return []\n",
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
    "        sample_dict = {\"premises-NL\": nl_list, \"premises-FOL\": fol_list}\n",
    "        if \"split\" in item:\n",
    "            sample_dict[\"split\"] = item[\"split\"]\n",
    "        samples.append(sample_dict)\n",
    "        \n",
    "    print(f\"Loaded {len(samples)} unique translation samples from {os.path.basename(path)}\")\n",
    "    return samples\n",
    "\n",
    "raw_samples_aug = load_translation_dataset(merged_path)\n",
    "raw_samples_no_aug = load_translation_dataset(no_aug_path)\n"
]

target_cell["source"] = new_source

with open(ipynb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Successfully patched loading cell in folc.ipynb!")
