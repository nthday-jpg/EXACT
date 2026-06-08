import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
notebooks = [
    root / "src" / "llm" / "tuning" / "fol.ipynb",
    root / "src" / "llm" / "tuning" / "fol_and_physics.ipynb"
]

target_code = """        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )"""

replacement_code = """        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )"""

for nb_path in notebooks:
    if not nb_path.exists():
        print(f"Skipping {nb_path} because it does not exist.")
        continue
        
    print(f"Patching repetition penalty in {nb_path.name}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
            
        source_str = "".join(cell.get("source", []))
        if target_code in source_str:
            source_str = source_str.replace(target_code, replacement_code)
            # Re-split into lines with newlines
            lines = [line + "\n" for line in source_str.split("\n")]
            if lines and lines[-1] == "\n":
                lines.pop()
            if lines:
                lines[-1] = lines[-1].rstrip("\n")
            cell["source"] = lines
            patched = True
            print(f"  -> Replaced successfully in a code cell.")
            
    if patched:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully saved {nb_path.name}")
    else:
        print(f"Failed to find model.generate block in {nb_path.name}")
