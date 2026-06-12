import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\src\llm\tuning\fol.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for idx, cell in enumerate(nb.get("cells", [])):
    if cell.get("cell_type") == "code":
        source = "".join(cell.get("source", []))
        if "def check_sample_with_z3" in source:
            print(f"=== Cell {idx} ===")
            lines = source.split("\n")
            start = -1
            for l_idx, line in enumerate(lines):
                if "def check_sample_with_z3" in line:
                    start = l_idx
                    break
            if start != -1:
                # Print 150 lines
                for k in range(start, min(start + 150, len(lines))):
                    print(lines[k])
            print("=" * 50)
            break
