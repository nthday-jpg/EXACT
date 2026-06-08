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
                new_lines = []
                in_helper = False
                
                for line in source_lines:
                    # Clean up any existing incorrectly unindented/partially indented lines
                    # If we find def lowercase_constants_and_variables
                    if "def lowercase_constants_and_variables(formula: str) -> str:" in line:
                        in_helper = True
                        # Clean line to be exactly 4 spaces indented
                        line = "    def lowercase_constants_and_variables(formula: str) -> str:\n"
                        new_lines.append(line)
                        continue
                    
                    # If we find class Z3Symbols
                    if "class Z3Symbols:" in line:
                        in_helper = False
                        line = "    class Z3Symbols:\n"
                        new_lines.append(line)
                        continue
                        
                    if in_helper:
                        # Strip all existing leading spaces and add exactly 4 extra spaces
                        # to whatever indentation was there originally
                        stripped = line.lstrip()
                        if stripped:
                            # Figure out original indentation level (relative to the unindented def)
                            # The original text was:
                            # def lowercase... (0 spaces)
                            #     reserved... (4 spaces)
                            #     def repl... (4 spaces)
                            #         word... (8 spaces)
                            # So we just add 4 spaces to the original relative indentation.
                            # First, let's find the original indentation in the line before we touched it:
                            # Let's count leading spaces of the line.
                            leading_spaces = len(line) - len(line.lstrip(' '))
                            # If it was unindented (e.g. 0 or 4 spaces relative to now), let's fix it:
                            # Let's see: if the line starts with "    " but was at the top level, we add 4 more spaces.
                            # Actually, a simpler way is: if the line was already modified and has 4 spaces,
                            # but should have 8 spaces (for body), let's check:
                            # reserved, def repl, return re.sub should have 8 spaces.
                            # word, if word..., return word, return word.lower() should have 12 spaces.
                            if stripped.startswith("reserved =") or stripped.startswith("def repl") or stripped.startswith("return re.sub"):
                                line = "        " + stripped
                            elif stripped.startswith("word =") or stripped.startswith("if word") or stripped.startswith("return word"):
                                line = "            " + stripped
                            else:
                                line = "    " + line.strip() + "\n"
                        else:
                            line = "\n"
                                
                    new_lines.append(line)
                
                cell["source"] = new_lines
                patched = True
                
    if patched:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully fixed indentation in {path}")
    else:
        print(f"Could not find target cell in {path}")
