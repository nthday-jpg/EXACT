import json
from pathlib import Path

notebook_paths = [
    Path("src/llm/tuning/fol.ipynb"),
    Path("src/llm/tuning/fol_and_physics.ipynb")
]

target_helper_lines = [
    "    def lowercase_constants_and_variables(formula: str) -> str:\n",
    "        reserved = {\"ForAll\", \"Exists\", \"AND\", \"OR\", \"NOT\", \"In\", \"implies\", \"BICOND\", \"IMPLIES\"}\n",
    "        def repl(match):\n",
    "            word = match.group(1)\n",
    "            if word in reserved or word.isdigit():\n",
    "                return word\n",
    "            return word.lower()\n",
    "        return re.sub(r\"\\b([A-Za-z_][A-Za-z0-9_]*)\\b(?!\\s*\\()\", repl, formula)\n",
    "\n"
]

for path in notebook_paths:
    if not path.exists():
        print(f"Skipping {path} (not found)")
        continue
        
    print(f"Applying perfect helper indentation in {path}...")
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            source_lines = cell["source"]
            source = "".join(source_lines)
            
            if "def lowercase_constants_and_variables" in source and "class Z3Symbols:" in source:
                # Find start index of def lowercase_constants_and_variables
                start_idx = -1
                end_idx = -1
                for idx, line in enumerate(source_lines):
                    if "def lowercase_constants_and_variables" in line:
                        start_idx = idx
                    if "class Z3Symbols:" in line:
                        end_idx = idx
                        break
                        
                if start_idx != -1 and end_idx != -1:
                    # Replace lines between start_idx and end_idx (non-inclusive of end_idx)
                    # and ensure class Z3Symbols line is exactly: "    class Z3Symbols:\n"
                    new_source_lines = source_lines[:start_idx] + target_helper_lines
                    
                    z3_symbols_line = "    class Z3Symbols:\n"
                    new_source_lines.append(z3_symbols_line)
                    new_source_lines.extend(source_lines[end_idx+1:])
                    
                    cell["source"] = new_source_lines
                    patched = True
                    
    if patched:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully applied helper indentation in {path}")
    else:
        print(f"Could not find target cell in {path}")
