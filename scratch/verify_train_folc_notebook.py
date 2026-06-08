import json
import sys

def verify_notebook():
    path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        print("Verification: Notebook is a valid JSON document.")
    except Exception as e:
        print(f"Error parsing notebook JSON: {e}")
        sys.exit(1)
        
    print(f"Loaded notebook with {len(nb['cells'])} cells.")
    
    for idx, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        source_str = "".join(cell["source"])
        print(f"\nChecking syntax of cell {idx}...")
        try:
            compile(source_str, f"cell_{idx}", "exec")
            print(f"Cell {idx} compiled successfully.")
        except SyntaxError as e:
            print(f"Syntax error in Cell {idx}: {e}")
            lines = source_str.splitlines()
            for line_idx, line in enumerate(lines):
                if abs(line_idx + 1 - e.lineno) <= 5:
                    marker = " -> " if line_idx + 1 == e.lineno else "    "
                    print(f"{marker}{line_idx+1}: {line}")
            sys.exit(1)
        except Exception as e:
            print(f"Error checking Cell {idx}: {e}")
            sys.exit(1)
            
    print("\nAll checks passed successfully!")

if __name__ == "__main__":
    verify_notebook()
