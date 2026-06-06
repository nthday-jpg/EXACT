import json

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Let's check if there is already a cell that calls train_model or evaluate
has_call = False
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "train_model(" in source and "def train_model" not in source:
            has_call = True
            break

if not has_call:
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "id": "e932b1a8",
        "metadata": {},
        "outputs": [],
        "source": [
            "# 7. Start Training and Post-Training Evaluation\n",
            "train_model(train_dataset, val_dataset, OUTPUT_DIR)"
        ]
    }
    nb["cells"].append(new_cell)
    print("Added training call cell to the end of the notebook.")
else:
    print("Notebook already has a training call.")

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Saved notebook successfully!")
