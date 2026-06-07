import json
import os

NOTEBOOK_PATH = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

print(f"Loading {NOTEBOOK_PATH}...")
with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

print("Patching cell 'e623797c' (Cell 1) and '0ece368f' (Cell 6)...")

# 1. Patch Cell 1 (e623797c)
cell_1 = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code" and cell.get("id") == "e623797c":
        cell_1 = cell
        break

if cell_1:
    source = cell_1["source"]
    # Check if sys.path code is already present
    if not any("sys.path.append" in line for line in source):
        # Insert after imports
        insert_idx = 5 # after import glob
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
    print("Warning: Cell 1 (e623797c) not found.")

# 2. Patch Cell 6 (0ece368f)
cell_6 = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code" and cell.get("id") == "0ece368f":
        cell_6 = cell
        break

if cell_6:
    source = cell_6["source"]
    # Find evaluate_fol_accuracy definition
    def_idx = -1
    for idx, line in enumerate(source):
        if "def evaluate_fol_accuracy" in line:
            def_idx = idx
            break
            
    if def_idx != -1:
        # Check if already patched
        if not any("sys.path.append" in source[i] for i in range(def_idx, def_idx + 15)):
            path_code = [
                "    # Ensure repository root is in sys.path to allow importing from src\n",
                "    for path in [\n",
                "        os.path.abspath(os.path.join(os.getcwd(), \"..\", \"..\", \"..\")),\n",
                "        \"/kaggle/working\",\n",
                "        os.getcwd()\n",
                "    ]:\n",
                "        if os.path.exists(path) and path not in sys.path:\n",
                "            sys.path.append(path)\n",
                "    \n"
            ]
            cell_6["source"] = source[:def_idx + 1] + path_code + source[def_idx + 1:]
            print("Patched evaluate_fol_accuracy in Cell 6 successfully.")
        else:
            print("evaluate_fol_accuracy in Cell 6 is already patched.")
    else:
        print("Warning: evaluate_fol_accuracy definition not found in Cell 6.")
else:
    print("Warning: Cell 6 (0ece368f) not found.")

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Finished patching train_folc_kaggle.ipynb!")
