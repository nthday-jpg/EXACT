import json
from pathlib import Path

notebook_paths = [
    Path("src/llm/tuning/fol.ipynb"),
    Path("src/llm/tuning/fol_and_physics.ipynb")
]

for path in notebook_paths:
    if not path.exists():
        print(f"Skipping {path} (not found)")
        continue
        
    print(f"Fixing indentation in {path}...")
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            source_lines = cell["source"]
            source = "".join(source_lines)
            
            # Check if this is the target cell
            if "class Z3Symbols:" in source and "class TokenStream:" in source:
                # We need to find lowercase_constants_and_variables and class Z3Symbols and indent them by 4 spaces.
                # Let's inspect the lines and adjust their indentation.
                new_lines = []
                in_helper = False
                
                for line in source_lines:
                    # If we find def lowercase_constants_and_variables
                    if "def lowercase_constants_and_variables(formula: str) -> str:" in line:
                        in_helper = True
                    
                    # If we find class Z3Symbols
                    if "class Z3Symbols:" in line:
                        in_helper = False
                        # Ensure class Z3Symbols has exactly 4 spaces indentation
                        line = "    class Z3Symbols:\n"
                        
                    if in_helper:
                        # Indent all lines inside lowercase_constants_and_variables by 4 spaces
                        # Skip empty lines or lines that already have enough spaces
                        if line.strip():
                            if not line.startswith("    "):
                                line = "    " + line
                                
                    new_lines.append(line)
                
                cell["source"] = new_lines
                patched = True
                
    if patched:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully fixed indentation in {path}")
    else:
        print(f"Could not find target cell in {path}")
