import json
import os

SOLVER_PATH = r"d:\mduy\source\repos\EXACT\src\physics\instructions\solver.md"
FOLC_NOTEBOOK_PATH = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"
PHYSICS_NOTEBOOK_PATH = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_physics_kaggle.ipynb"

# 1. Read solver prompt content
print(f"Reading prompt from: {SOLVER_PATH}")
with open(SOLVER_PATH, "r", encoding="utf-8") as f:
    new_prompt = f.read().strip()

def update_prompt_in_cell(cell, new_prompt):
    source_str = "".join(cell["source"])
    # Find physics_system_prompt = """
    key = 'physics_system_prompt = """'
    idx = source_str.find(key)
    if idx == -1:
        key = "physics_system_prompt = '''"
        idx = source_str.find(key)
        if idx == -1:
            raise ValueError("physics_system_prompt variable not found in cell source")
            
    prompt_start = idx + len(key)
    close_quote = '"""' if '"""' in key else "'''"
    prompt_end = source_str.find(close_quote, prompt_start)
    if prompt_end == -1:
        raise ValueError("Closing triple quotes for physics_system_prompt not found")
        
    # Replace the text inside the triple quotes
    new_source_str = source_str[:prompt_start] + new_prompt + source_str[prompt_end:]
    
    # Split back into lines
    lines = []
    current_line = []
    for char in new_source_str:
        current_line.append(char)
        if char == '\n':
            lines.append("".join(current_line))
            current_line = []
    if current_line:
        lines.append("".join(current_line))
        
    cell["source"] = lines

def process_notebook(path, target_cell_id):
    print(f"Processing notebook: {path}...")
    if not os.path.exists(path):
        print(f"  Error: Notebook file does not exist at {path}")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    found = False
    for cell in nb["cells"]:
        if cell.get("id") == target_cell_id:
            try:
                update_prompt_in_cell(cell, new_prompt)
                found = True
                print(f"  Success: Updated prompt in cell with ID '{target_cell_id}'")
            except Exception as e:
                print(f"  Error updating prompt in cell: {e}")
                return False
            break
            
    if not found:
        print(f"  Error: Cell with ID '{target_cell_id}' not found.")
        return False
        
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"  Saved notebook: {path}")
    return True

if __name__ == "__main__":
    # Update folc kaggle notebook (Cell 3 ID: 3e47b246)
    folc_success = process_notebook(FOLC_NOTEBOOK_PATH, "3e47b246")
    
    # Update physics kaggle notebook (Cell 3 ID: data_loading)
    phys_success = process_notebook(PHYSICS_NOTEBOOK_PATH, "data_loading")
    
    if folc_success and phys_success:
        print("\nAll notebooks updated successfully!")
    else:
        print("\nSome notebook updates failed.")
        exit(1)
