import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\src\llm\tuning\fol.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

cell = nb.get("cells", [])[4]
print("".join(cell.get("source", [])))
