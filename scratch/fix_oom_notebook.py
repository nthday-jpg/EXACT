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
    if "# 2. TRAINING HYPERPARAMETERS" in source_str:
        print(f"Patching hyperparams in cell 2 at index {idx}...")
        
        new_source = []
        for line in source:
            if "GRADIENT_CHECKPOINTING = False" in line:
                new_source.append("GRADIENT_CHECKPOINTING = True\n")
            elif "BATCH_SIZE = 16" in line:
                new_source.append("BATCH_SIZE = 8             # Adjusted for stable VRAM overhead\n")
            elif "GRADIENT_ACCUMULATION = 1" in line:
                new_source.append("GRADIENT_ACCUMULATION = 2   # Adjusted to maintain effective batch size of 16 (8 * 2 = 16)\n")
            else:
                new_source.append(line)
        
        cell["source"] = new_source
        patched = True
        break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook hyperparameters adjusted successfully for OOM prevention!")
else:
    print("Could not find Cell 2 in notebook.")
