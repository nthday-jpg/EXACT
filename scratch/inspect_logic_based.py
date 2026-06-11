import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

sources = {}
logic_based_mismatches = 0
for item in data:
    src = item.get("dataset_source", "unknown")
    sources[src] = sources.get(src, 0) + 1
    
    if src == "logic_based":
        nl = item.get("premises-NL", [])
        fol = item.get("premises-FOL", [])
        # Check if the content is completely different
        # Let's count how many have rules in FOL but no rules in NL
        nl_has_rules = any("if" in x.lower() or "all" in x.lower() or "every" in x.lower() or "no" in x.lower() for x in nl)
        fol_has_rules = any("ForAll" in x or "Exists" in x for x in fol)
        if fol_has_rules and not nl_has_rules:
            logic_based_mismatches += 1

print("Dataset sources distribution:")
for src, count in sources.items():
    print(f"  - {src}: {count}")

print(f"Logic based items with rules in FOL but no rules in NL: {logic_based_mismatches} / {sources.get('logic_based', 0)}")
