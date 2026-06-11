import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
    failed_cases = json.load(f)

count = 0
for item in failed_cases:
    eid = item.get("example_id")
    gt = item.get("premises-FOL-GT", [])
    pred = item.get("premises-FOL-Pred", [])
    
    if len(gt) != len(pred):
        continue
        
    has_math_op = False
    for g, p in zip(gt, pred):
        p_str = str(p).strip()
        g_str = str(g).strip()
        if any(op in p_str for op in ["<=", ">=", "=", "<", ">"]) and not any(op in g_str for op in ["<=", ">=", "=", "<", ">"]):
            has_math_op = True
            break
            
    if has_math_op:
        count += 1
        print(f"\nMath operator Example {count} (ID: {eid})")
        print("NL Premises:")
        for p in item.get("premises-NL", []):
            print(f"  - {p}")
        print("GT:")
        for p in gt:
            print(f"  - {p}")
        print("Pred:")
        for p in pred:
            print(f"  - {p}")
        if count >= 5:
            break
