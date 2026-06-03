import json
import os

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

if not os.path.exists(notebook_path):
    print("Notebook path not found")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

patched = False
for cell in nb.get("cells", []):
    source = cell.get("source", [])
    if not source:
        continue
    source_str = "".join(source)
    if "# 4. Initialize Tokenizer and load Base Model" in source_str:
        new_source = []
        for line in source:
            if "torch_dtype=" in line:
                new_line = line.replace("torch_dtype=", "dtype=")
                new_source.append(new_line)
                patched = True
            else:
                new_source.append(line)
        cell["source"] = new_source
        break

if patched:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook updated successfully: replaced torch_dtype with dtype in Cell 4.")
else:
    print("Could not find torch_dtype in Cell 4.")
