import json
from pathlib import Path

nb_path = Path("d:/mduy/source/repos/EXACT/src/llm/tuning/fol_and_physics.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

keywords = ["system_prompt_template", "user_prompt_template", "prepare_dataset", "prompt", "glossary"]

for idx, cell in enumerate(nb.get("cells", [])):
    if cell.get("cell_type") == "code":
        source = "".join(cell.get("source", []))
        for kw in keywords:
            if kw in source:
                print(f"--- Cell {idx} contains '{kw}' ---")
                # print first 10 lines of cell
                lines = source.split("\n")
                for line in lines[:25]:
                    print(line)
                if len(lines) > 25:
                    print("...")
                print()
                break
