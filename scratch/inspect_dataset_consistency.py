import json
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total samples in augmented dataset: {len(data)}")

# Count how many samples use math operators vs binary/unary names for numbers
has_math_op_count = 0
has_numeric_pred_count = 0  # like Seats300, Passengers100, etc.

# Count how many samples have domain restriction in ForAll/Exists
has_domain_rest_count = 0
has_no_domain_rest_count = 0

for item in data:
    fol_list = item.get("premises-FOL", [])
    
    uses_math_op = False
    uses_numeric_pred = False
    uses_domain_rest = False
    uses_no_domain_rest = False
    
    for fol in fol_list:
        fol_str = str(fol)
        # Math operators standalone check
        if re.search(r'(?<![-<])>(?!=)|(?<!-)<(?![=-])|>=|<=|!=|(?<![<>!=])=(?![=>])', fol_str):
            uses_math_op = True
            
        # Check for numeric predicates like Seats300 or Age25 or Passengers100
        if re.search(r'\b[A-Za-z_][A-Za-z0-9_-]*(?:300|100|25|2010|8)\b', fol_str):
            uses_numeric_pred = True
            
        # Check domain restriction in ForAll
        # E.g., ForAll(x, Category(x) -> ...
        if "ForAll(" in fol_str:
            # Let's see if the ForAll is restricted, i.e. ForAll(x, Something(x) -> ...
            # Simple pattern: ForAll(var, (Restricter(var) -> ...
            match = re.search(r'ForAll\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*(?:\()?\s*[A-Za-z_][A-Za-z0-9_]*\(\1\)\s*->', fol_str)
            if match:
                uses_domain_rest = True
            else:
                uses_no_domain_rest = True

    if uses_math_op:
        has_math_op_count += 1
    if uses_numeric_pred:
        has_numeric_pred_count += 1
    if uses_domain_rest:
        has_domain_rest_count += 1
    if uses_no_domain_rest:
        has_no_domain_rest_count += 1

print(f"Dataset Statistics:")
print(f"  - Samples with mathematical comparison operators in FOL: {has_math_op_count}")
print(f"  - Samples with hardcoded numbers in predicate names (e.g. Seats300): {has_numeric_pred_count}")
print(f"  - Samples with domain restriction (e.g. ForAll(x, Cat(x) -> ...)): {has_domain_rest_count}")
print(f"  - Samples without domain restriction (e.g. ForAll(x, Prop(x))): {has_no_domain_rest_count}")
