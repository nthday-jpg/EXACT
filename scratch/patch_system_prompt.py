import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
notebooks = [
    root / "src" / "llm" / "tuning" / "fol.ipynb",
    root / "src" / "llm" / "tuning" / "fol_and_physics.ipynb"
]

old_block = [
    "system_prompt_template = (\n",
    '    "You convert natural-language premises into parser-safe first-order logic formulas.\\n\\n"\n',
    '    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\\n"\n',
    '    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\\n\\n"\n',
    '    "ALLOWED OPERATORS:\\n"\n',
    '    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\\n\\n"\n',
    '    "QUANTIFIER RULES:\\n"\n',
    '    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\\n\\n"\n',
    '    "Return JSON only."\n',
    ")\n"
]

new_block = [
    "system_prompt_template = (\n",
    '    "You convert natural-language premises into parser-safe first-order logic formulas.\\n\\n"\n',
    '    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\\n"\n',
    '    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\\n\\n"\n',
    '    "ALLOWED OPERATORS:\\n"\n',
    '    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\\n\\n"\n',
    '    "QUANTIFIER RULES:\\n"\n',
    '    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\\n\\n"\n',
    '    "NUMERICAL ATTRIBUTES & COMPARISONS:\\n"\n',
    '    "Represent numerical attributes (e.g., age, score, GPA, duration, credits) as functions mapping to a number, and compare using operators (=, !=, >=, <=, >, <).\\n"\n',
    '    "E.g., \\"John has a GPA of 3.8\\" -> GPA(john) = 3.8\\n"\n',
    '    "E.g., \\"GPA is at least 3.5\\" -> ForAll(x, GPA(x) >= 3.5 -> ...)\\n"\n',
    '    "Do NOT use binary predicates like GPA(john, 3.8).\\n\\n"\n',
    '    "DOMAIN RESTRICTION RULE:\\n"\n',
    '    "Restrict the domain of quantified variables to the relevant category.\\n"\n',
    '    "E.g., \\"All students are happy\\" -> ForAll(x, Student(x) -> Happy(x))\\n"\n',
    '    "Do NOT write ForAll(x, Happy(x)).\\n\\n"\n',
    '    "Return JSON only."\n',
    ")\n"
]

for nb_path in notebooks:
    if not nb_path.exists():
        print(f"Skipping {nb_path} because it does not exist.")
        continue
        
    print(f"Patching system prompt in {nb_path.name}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
            
        source = cell.get("source", [])
        # Check if the block is in the source
        # Since lines in notebook might have slightly different trailing spaces or quotes,
        # we will do a search and replace on the joined source string.
        source_str = "".join(source)
        
        target_str = "".join(old_block)
        replacement_str = "".join(new_block)
        
        if target_str in source_str:
            source_str = source_str.replace(target_str, replacement_str)
            # Re-split into lines with newlines
            lines = [line + "\n" for line in source_str.split("\n")]
            if lines and lines[-1] == "\n":
                lines.pop()
            if lines:
                lines[-1] = lines[-1].rstrip("\n")
            cell["source"] = lines
            patched = True
            print(f"  -> Replaced successfully in code cell.")
            break
            
    if patched:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Successfully saved {nb_path.name}")
    else:
        print(f"Failed to find target prompt block in {nb_path.name}")
