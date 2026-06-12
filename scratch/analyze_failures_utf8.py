import json
import sys
import re

# Set stdout to utf-8 to avoid Windows console errors
sys.stdout.reconfigure(encoding='utf-8')

def analyze():
    with open(r"d:\mduy\source\repos\EXACT\data\fol_failed_cases.json", "r", encoding="utf-8") as f:
        failed_cases = json.load(f)

    print(f"Total failed cases loaded: {len(failed_cases)}")

    # Categorization counts
    mismatched_length = 0
    syntax_invalid = 0
    json_invalid = 0
    qa_incorrect = 0
    qa_correct = 0
    
    # Types of formula mismatches (for cases where len(GT) == len(Pred))
    quantifier_restrictor_mismatch = 0  # e.g., Pred has Student(x) -> but GT doesn't
    predicate_naming_mismatch = 0       # e.g., Park(x) vs GoToPark(x)
    logical_structure_mismatch = 0      # e.g., -> vs AND, or operator scope
    constant_naming_mismatch = 0        # e.g., james vs James
    exact_same_after_whitespace = 0     # matched after simple stripping/whitespace norm
    missing_rules_in_nl = 0             # GT has rules like ForAll, but NL/Pred only have facts

    for item in failed_cases:
        example_id = item.get("example_id")
        nl = item.get("premises-NL", [])
        gt = item.get("premises-FOL-GT", [])
        pred = item.get("premises-FOL-Pred", [])
        is_qa_corr = item.get("is_qa_correct", False)
        is_j_val = item.get("is_json_valid", False)
        is_s_val = item.get("is_syntax_valid", False)

        if not is_j_val:
            json_invalid += 1
            continue
        if not is_s_val:
            syntax_invalid += 1
            continue
        
        if is_qa_corr:
            qa_correct += 1
        else:
            qa_incorrect += 1

        if len(gt) != len(pred):
            mismatched_length += 1
            # Check if GT has more formulas and they are rules
            gt_has_rules = any("ForAll" in f or "Exists" in f for f in gt)
            pred_has_rules = any("ForAll" in f or "Exists" in f for f in pred)
            if gt_has_rules and not pred_has_rules:
                missing_rules_in_nl += 1
            continue

        # Let's analyze formula by formula mismatches
        has_restrictor_diff = False
        has_naming_diff = False
        has_logical_diff = False
        has_const_diff = False
        has_ws_diff = False

        for g_f, p_f in zip(gt, pred):
            g_f = str(g_f).strip()
            p_f = str(p_f).strip()
            if g_f == p_f:
                continue
            
            # 1. Whitespace differences
            if g_f.replace(" ", "") == p_f.replace(" ", ""):
                has_ws_diff = True
                continue

            # 2. Check for domain restrictors like Student(x) -> or Person(x) -> in pred but missing in gt
            # e.g., "Student(x) AND" or "Student(x) ->"
            g_no_rest = re.sub(r'\b(Student|Person|Animal|Plane|Country|Object|Item|x)\(x\)\s*(->|AND)\s*', '', g_f, flags=re.IGNORECASE)
            p_no_rest = re.sub(r'\b(Student|Person|Animal|Plane|Country|Object|Item|x)\(x\)\s*(->|AND)\s*', '', p_f, flags=re.IGNORECASE)
            if g_no_rest.replace(" ", "") == p_no_rest.replace(" ", ""):
                has_restrictor_diff = True
                continue

            # 3. Predicate naming differences (e.g., Park(x) vs GoToPark(x) or Movies(x) vs GoToMovies(x))
            # If we strip non-alphabetic characters and standard operators, do they map?
            # Let's do a simple check: if we unify predicate names, do they match?
            # We will count this as naming diff
            has_naming_diff = True

            # 4. Check for logical structure difference (e.g. ForAll(x, A -> B) vs ForAll(x, A) -> ForAll(y, B))
            if "ForAll" in g_f and "ForAll" in p_f:
                # If they have different quantifiers or structures
                pass

        if has_restrictor_diff:
            quantifier_restrictor_mismatch += 1
        if has_naming_diff:
            predicate_naming_mismatch += 1
        if has_ws_diff:
            exact_same_after_whitespace += 1

    print("\n=== Failure Analysis ===")
    print(f"Total Failed Cases: {len(failed_cases)}")
    print(f"  - Invalid JSON: {json_invalid}")
    print(f"  - Invalid Syntax: {syntax_invalid}")
    print(f"  - Mismatched formula count (GT vs Pred): {mismatched_length}")
    print(f"    - of which GT has rules omitted in NL/Pred: {missing_rules_in_nl}")
    print(f"  - Exact same after whitespace stripping: {exact_same_after_whitespace}")
    print(f"  - Quantifier Domain Restrictor Mismatch: {quantifier_restrictor_mismatch}")
    print(f"  - Predicate/Constant Naming Mismatch: {predicate_naming_mismatch}")
    print(f"  - Downstream QA is Correct: {qa_correct}")
    print(f"  - Downstream QA is Incorrect: {qa_incorrect}")

    # Let's print 5 samples of mismatched formula count to see why
    print("\n--- Samples of Mismatched Formula Count ---")
    count = 0
    for item in failed_cases:
        gt = item.get("premises-FOL-GT", [])
        pred = item.get("premises-FOL-Pred", [])
        if len(gt) != len(pred) and count < 5:
            print(f"\nID: {item.get('example_id')}")
            print("NL Premises:")
            for p in item.get("premises-NL", []):
                print(f"  - {p}")
            print(f"GT FOL (len={len(gt)}):")
            for p in gt:
                print(f"  - {p}")
            print(f"Pred FOL (len={len(pred)}):")
            for p in pred:
                print(f"  - {p}")
            count += 1

if __name__ == "__main__":
    analyze()
