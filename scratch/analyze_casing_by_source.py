import json
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

source_stats = defaultdict(lambda: {"total": 0, "math_op": 0, "numeric_pred": 0, "domain_rest": 0, "no_domain_rest": 0})

for item in data:
    src = item.get("dataset_source", "unknown")
    # Simplify source name (group augmented together)
    simple_src = src.split("-augmented")[0].split("-canonicalized")[0]
    
    fol_list = item.get("premises-FOL", [])
    
    uses_math_op = False
    uses_numeric_pred = False
    uses_domain_rest = False
    uses_no_domain_rest = False
    
    for fol in fol_list:
        fol_str = str(fol)
        if re.search(r'(?<![-<])>(?!=)|(?<!-)<(?![=-])|>=|<=|!=|(?<![<>!=])=(?![=>])', fol_str):
            uses_math_op = True
        if re.search(r'\b[A-Za-z_][A-Za-z0-9_-]*(?:300|100|25|2010|8)\b', fol_str):
            uses_numeric_pred = True
        if "ForAll(" in fol_str:
            match = re.search(r'ForAll\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*(?:\()?\s*[A-Za-z_][A-Za-z0-9_]*\(\1\)\s*->', fol_str)
            if match:
                uses_domain_rest = True
            else:
                uses_no_domain_rest = True

    stats = source_stats[simple_src]
    stats["total"] += 1
    if uses_math_op:
        stats["math_op"] += 1
    if uses_numeric_pred:
        stats["numeric_pred"] += 1
    if uses_domain_rest:
        stats["domain_rest"] += 1
    if uses_no_domain_rest:
        stats["no_domain_rest"] += 1

print(f"{'Source':<30} | {'Total':<6} | {'Math Op':<7} | {'Num Pred':<8} | {'Dom Rest':<8} | {'No Dom Rest':<11}")
print("-" * 80)
for src, stats in sorted(source_stats.items()):
    print(f"{src:<30} | {stats['total']:<6} | {stats['math_op']:<7} | {stats['numeric_pred']:<8} | {stats['domain_rest']:<8} | {stats['no_domain_rest']:<11}")
