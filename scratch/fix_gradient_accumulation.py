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
        print(f"Found Cell 2 (Training Hyperparameters) at index {idx}.")
        new_source = []
        skip_next = False
        for line in source:
            if "BATCH_SIZE = 8" in line:
                if not any("GRADIENT_ACCUMULATION" in l for l in new_source):
                    new_source.append("BATCH_SIZE = 8             # Adjusted for stable VRAM overhead\n")
                    new_source.append("GRADIENT_ACCUMULATION = 2  # Gradient accumulation steps (Effective batch size = 16)\n")
                # skip duplicates/subsequent BATCH_SIZE = 8 lines
                continue
            else:
                new_source.append(line)
        cell["source"] = new_source
        patched = True
        break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook updated successfully with GRADIENT_ACCUMULATION = 2 and duplicate BATCH_SIZE removed!")
else:
    print("Could not find Cell 2 in the notebook.")
