import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
notebooks = [
    root / "src" / "llm" / "tuning" / "fol.ipynb",
    root / "src" / "llm" / "tuning" / "fol_and_physics.ipynb"
]

target_line = "fallback_fol.append(translate_single_sentence(model, tokenizer, s))"
replacement_line = "fallback_fol.append(translate_single_sentence(model, tokenizer, s, glossary_str=glossary_str))"

for nb_path in notebooks:
    if not nb_path.exists():
        print(f"Skipping {nb_path} because it does not exist.")
        continue
        
    print(f"Patching {nb_path.name}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        
        source = cell.get("source", [])
        for idx, line in enumerate(source):
            if target_line in line:
                source[idx] = line.replace(target_line, replacement_line)
                patched = True
                print(f"  -> Replaced on line {idx+1}")
                
    if patched:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully saved patched {nb_path.name}")
    else:
        print(f"No changes made to {nb_path.name}")
