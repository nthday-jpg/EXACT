import json
import os

NOTEBOOK_PATH = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_physics_kaggle.ipynb"

print(f"Loading {NOTEBOOK_PATH}...")
with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

print("Patching cell 'env_setup' (Cell 1)...")

# Find Cell 1 (env_setup)
cell_1 = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code" and cell.get("id") == "env_setup":
        cell_1 = cell
        break

if cell_1:
    source = cell_1["source"]
    # Check if sys.path code is already present
    if not any("sys.path.append" in line for line in source):
        # Insert after imports (index 5)
        insert_idx = 5
        path_code = [
            "\n",
            "# Add repository root and working directories to sys.path to allow importing from src\n",
            "for path in [\n",
            "    os.path.abspath(os.path.join(os.getcwd(), \"..\", \"..\", \"..\")),\n",
            "    \"/kaggle/working\",\n",
            "    os.getcwd()\n",
            "]:\n",
            "    if os.path.exists(path) and path not in sys.path:\n",
            "        sys.path.append(path)\n"
        ]
        cell_1["source"] = source[:insert_idx] + path_code + source[insert_idx:]
        print("Patched Cell 1 successfully.")
    else:
        print("Cell 1 is already patched.")
else:
    print("Warning: Cell 1 not found.")

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Finished patching train_physics_kaggle.ipynb!")
