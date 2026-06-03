import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

if not os.path.exists(notebook_path):
    print(f"Error: Notebook not found")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

patched = False
for cell in nb.get("cells", []):
    source = cell.get("source", [])
    if not source:
        continue
    source_str = "".join(source)
    if "# 2. TRAINING HYPERPARAMETERS" in source_str:
        # We will directly rebuild the source lines for this cell cleanly
        new_source = []
        for line in source:
            # Skip any existing GRADIENT_ACCUMULATION lines or BATCH_SIZE lines inside this block, 
            # we will insert them cleanly in the correct position.
            if "BATCH_SIZE =" in line or "GRADIENT_ACCUMULATION =" in line:
                continue
            new_source.append(line)
        
        # Now find where the '# --- Training Hyperparameters ---' comment is, and insert after it
        inserted = False
        for idx, line in enumerate(new_source):
            if "# --- Training Hyperparameters ---" in line:
                new_source.insert(idx + 1, "MAX_LENGTH = 768            # Maximum sequence length\n")
                new_source.insert(idx + 2, "BATCH_SIZE = 8             # Adjusted for stable VRAM overhead\n")
                new_source.insert(idx + 3, "GRADIENT_ACCUMULATION = 2  # Gradient accumulation steps (Effective batch size = 16)\n")
                inserted = True
                break
        
        # Clean up duplicates of MAX_LENGTH if any
        final_source = []
        seen_max_len = False
        for line in new_source:
            if "MAX_LENGTH = 768" in line:
                if seen_max_len:
                    continue
                seen_max_len = True
            final_source.append(line)
            
        cell["source"] = final_source
        patched = True
        break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook updated successfully with clean hyperparameters block!")
else:
    print("Failed to patch notebook.")
