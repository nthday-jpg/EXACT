import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

target_found = False
for idx, cell in enumerate(nb.get("cells", [])):
    source = cell.get("source", [])
    # Find the cell that starts with the specific comment or has logic_path
    if any("# 3. Search and load NL -> FOL translation datasets" in line for line in source):
        print(f"Found target cell at index {idx}")
        
        # Define the new source code lines for this cell
        new_source = [
            "# 3. Search and load NL -> FOL translation datasets\n",
            "import os\n",
            "import glob\n",
            "import json\n",
            "\n",
            "merged_path = \"/kaggle/input/datasets/mduy2911/folc-train/merged_valid.json\"\n",
            "if not os.path.exists(merged_path):\n",
            "    # Fallback to local files or look in the current working directory\n",
            "    candidates = glob.glob(\"**/merged_valid.json\", recursive=True) + glob.glob(\"merged_valid.json\")\n",
            "    if candidates:\n",
            "        merged_path = candidates[0]\n",
            "    else:\n",
            "        raise FileNotFoundError(\n",
            "            \"Could not find merged_valid.json.\\n\"\n",
            "            \"Please upload it to /kaggle/working/ or add it as a Kaggle Dataset.\"\n",
            "        )\n",
            "\n",
            "print(f\"Using merged dataset path: {merged_path}\")\n",
            "\n",
            "def load_translation_dataset(path):\n",
            "    samples = []\n",
            "    seen_premises = set()\n",
            "    \n",
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
            "        samples.append({\"premises-NL\": nl_list, \"premises-FOL\": fol_list})\n",
            "    print(f\"Loaded {len(samples)} unique samples from {os.path.basename(path)}\")\n",
            "    return samples\n",
            "\n",
            "raw_samples = load_translation_dataset(merged_path)\n"
        ]
        
        cell["source"] = new_source
        target_found = True
        break

if target_found:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Successfully updated notebook cell 3!")
else:
    print("Target cell not found!")
