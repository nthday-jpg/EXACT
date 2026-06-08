import json

with open("src/llm/tuning/fol.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

output_lines = []
for idx, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "def translate_sentences" in source or "def check_sample_with_z3" in source:
            output_lines.append(f"=== CELL {idx} ===")
            output_lines.append(source)
            output_lines.append("\n" + "="*50 + "\n")

with open("scratch/extracted_nb_funcs.txt", "w", encoding="utf-8") as f_out:
    f_out.write("\n".join(output_lines))

print("Wrote extracted functions to scratch/extracted_nb_funcs.txt")
