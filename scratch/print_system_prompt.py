import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\src\llm\tuning\fol.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        source = "".join(cell.get("source", []))
        if "system_prompt_template" in source:
            print("=== Found Cell containing system_prompt_template ===")
            print(source)
            print("=" * 50)
