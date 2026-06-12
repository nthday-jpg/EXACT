import json
import sys
from pathlib import Path
import re

sys.stdout.reconfigure(encoding='utf-8')

def analyze_mismatches():
    with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
        failed_cases = json.load(f)

    categories = {
        "fact_rule_mismatch": [],       # NL has facts, Pred has facts, but GT has rules (e.g. 16_0)
        "domain_restriction": [],       # Pred has Student(x) -> or similar restrictors, GT does not
        "math_operator": [],            # Pred uses <=, =, > on functions, GT uses simple predicates
        "existential_implication": [],  # Pred/GT uses Exists(x, A -> B) instead of Exists(x, A AND B)
        "predicate_naming": [],         # Different word/phrase for same predicate (e.g. Park vs GoToPark)
        "logical_structure": [],        # Completely different logical formulas/implications (e.g. A OR B vs A <-> B)
        "other": []
    }

    # Math operator regex matching standalone <, >, <=, >=, !=, =
    # excluding -> and <->
    math_op_regex = re.compile(r'(?<![-<])>(?!=)|(?<!-)<(?![=-])|>=|<=|!=|(?<![<>!=])=(?![=>])')

    for item in failed_cases:
        eid = item.get("example_id")
        nl = item.get("premises-NL", [])
        gt = item.get("premises-FOL-GT", [])
        pred = item.get("premises-FOL-Pred", [])
        
        # Check if GT is empty or Pred is empty
        if not gt or not pred:
            categories["other"].append((eid, "Empty GT or Pred"))
            continue
            
        if len(gt) != len(pred):
            categories["other"].append((eid, f"Length mismatch: GT={len(gt)}, Pred={len(pred)}"))
            continue

        # Check for fact-rule mismatch (e.g., GT has ForAll rules, but NL/Pred only has facts about individuals)
        gt_has_forall = any("ForAll" in str(f) for f in gt)
        nl_has_forall = any(any(w in str(p).lower() for w in ["all", "every", "if", "each", "no "]) for p in nl)
        pred_has_forall = any("ForAll" in str(p) for p in pred)
        
        # If GT has ForAll but NL and Pred do not have general rule indicators
        if gt_has_forall and not pred_has_forall and not nl_has_forall:
            categories["fact_rule_mismatch"].append((eid, "GT has ForAll rules, NL & Pred only have facts"))
            continue

        # Check each formula pair
        has_domain_rest = False
        has_math_op = False
        has_exist_imp = False
        has_logical = False
        has_pred_naming = False

        for g, p in zip(gt, pred):
            g_str = str(g).strip()
            p_str = str(p).strip()
            if g_str == p_str:
                continue

            # 1. Math operator mismatch
            if math_op_regex.search(p_str) and not math_op_regex.search(g_str):
                has_math_op = True
                
            # 2. Existential implication
            # Check for Exists(..., ... -> ...)
            if "Exists" in p_str and "->" in p_str:
                has_exist_imp = True
            elif "Exists" in g_str and "->" in g_str:
                has_exist_imp = True

            # 3. Domain restriction mismatch
            # E.g., Pred has "Student(x) ->" or "Animal(x) ->" or similar, but GT has just the predicate
            if ("Student(" in p_str or "Person(" in p_str) and not ("Student(" in g_str or "Person(" in g_str):
                has_domain_rest = True

            # 4. Logical structure differences (AND/OR, different implication directions, parentheses structure)
            g_norm = g_str.replace(" ", "").replace("(", "").replace(")", "")
            p_norm = p_str.replace(" ", "").replace("(", "").replace(")", "")
            
            g_ops = set(re.findall(r'\b(AND|OR|NOT|->|<->)\b', g_str))
            p_ops = set(re.findall(r'\b(AND|OR|NOT|->|<->)\b', p_str))
            if g_ops != p_ops:
                has_logical = True

            # 5. Predicate naming mismatch
            if g_norm != p_norm and not has_logical and not has_math_op and not has_domain_rest:
                has_pred_naming = True

        if has_fact_rule_mismatch := (gt_has_forall and not pred_has_forall and not nl_has_forall):
            categories["fact_rule_mismatch"].append((eid, "GT has ForAll rules, NL & Pred only have facts"))
        elif has_math_op:
            categories["math_operator"].append((eid, "Math operators (e.g. <=, =, >) vs simple predicates"))
        elif has_domain_rest:
            categories["domain_restriction"].append((eid, "Pred restricts quantifiers to Student(x)/Person(x) etc. while GT does not"))
        elif has_exist_imp:
            categories["existential_implication"].append((eid, "Existential quantifier uses implication (->) instead of conjunction (AND)"))
        elif has_logical:
            categories["logical_structure"].append((eid, "Different logical structure or operators used"))
        elif has_pred_naming:
            categories["predicate_naming"].append((eid, "Predicate naming discrepancies (different verbs/nouns used)"))
        else:
            categories["other"].append((eid, "Other mismatch"))

    print("=== Category Counts (Corrected) ===")
    for cat, items in categories.items():
        print(f"  - {cat}: {len(items)}")

    # Print examples for each category to be super sure!
    for cat, items in categories.items():
        if not items:
            continue
        print(f"\n--- Examples of {cat} (Total: {len(items)}) ---")
        for eid, desc in items[:2]:
            # find item
            for item in failed_cases:
                if item.get("example_id") == eid:
                    print(f"ID: {eid} | Reason: {desc}")
                    print("  NL Premises:")
                    for p in item.get("premises-NL", [])[:3]:
                        print(f"    - {p}")
                    print("  GT FOL:")
                    for p in item.get("premises-FOL-GT", []):
                        print(f"    - {p}")
                    print("  Pred FOL:")
                    for p in item.get("premises-FOL-Pred", []):
                        print(f"    - {p}")
                    print()
                    break

if __name__ == "__main__":
    analyze_mismatches()
