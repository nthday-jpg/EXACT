import json
import os

notebook_paths = [
    r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb",
    r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_physics_kaggle.ipynb"
]

success = True
for notebook_path in notebook_paths:
    print(f"Loading notebook: {notebook_path}...")
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    print(f"Verifying cell syntax for {os.path.basename(notebook_path)}...")
    for idx, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            cell_id = cell.get("id", f"index_{idx}")
            source = "".join(cell["source"])
            if not source.strip():
                continue
            try:
                compile(source, f"Cell_{cell_id}", "exec")
                print(f"  Cell {cell_id}: Syntax OK")
            except SyntaxError as e:
                print(f"  Cell {cell_id}: SYNTAX ERROR!")
                print(f"    Line {e.lineno}: {e.text.strip() if e.text else ''}")
                print(f"    {e.msg}")
                success = False
            except Exception as e:
                print(f"  Cell {cell_id}: Compilation failed with: {e}")
                success = False
    print("-" * 50)

if success:
    print("Notebook cell validation: SUCCESS! All cells are syntactically valid python code.")
else:
    print("Notebook cell validation: FAILED!")
    exit(1)
