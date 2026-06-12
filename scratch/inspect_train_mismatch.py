import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

train_mismatches = 0
train_logic_based_total = 0

for item in data:
    if item.get("split") == "train" and item.get("dataset_source") == "logic_based":
        train_logic_based_total += 1
        nl = item.get("premises-NL", [])
        fol = item.get("premises-FOL", [])
        
        # Check if NL is facts but FOL contains ForAll rules
        nl_has_rules = any("if" in x.lower() or "all" in x.lower() or "every" in x.lower() or "no" in x.lower() for x in nl)
        fol_has_rules = any("ForAll" in x or "Exists" in x for x in fol)
        if fol_has_rules and not nl_has_rules:
            train_mismatches += 1

print(f"Total logic_based training samples: {train_logic_based_total}")
print(f"Number of them with mismatch (rules in FOL but no rules in NL): {train_mismatches}")
