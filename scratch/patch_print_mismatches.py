import json

ipynb_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

with open(ipynb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find Cell 6 (contains evaluate_fol_accuracy)
helper_cell = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "def evaluate_fol_accuracy" in source:
            helper_cell = cell
            break

if helper_cell:
    print("Found Cell 6. Patching evaluate_fol_accuracy to print mismatches...")
    source_lines = helper_cell["source"]
    source_text = "".join(source_lines)
    
    # We will target replacing the old try-except block of evaluate_fol_accuracy
    # Let's locate the target substring.
    target_pattern = """        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            if isinstance(parsed_response, list):
                predicted_premises_fol = [str(x).strip() for x in parsed_response]
                all_formulas_valid = True
                for formula in parsed_response:
                    if fol_parser_available:
                        try:
                            is_valid, _ = try_parse_fol(str(formula))
                            if not is_valid:
                                all_formulas_valid = False
                                break
                        except Exception:
                            if not basic_validate_fol(str(formula)):
                                all_formulas_valid = False
                                break
                    else:
                        if not basic_validate_fol(str(formula)):
                            all_formulas_valid = False
                            break
                if all_formulas_valid:
                    syntax_valid_count += 1
                
                if isinstance(fol_list_gt, list):
                    if [str(x).strip() for x in parsed_response] == [str(x).strip() for x in fol_list_gt]:
                        correct_count += 1
                    
                    matched_formulas = 0
                    for p_f, g_f in zip(parsed_response, fol_list_gt):
                        if str(p_f).strip() == str(g_f).strip():
                            matched_formulas += 1
                    formula_correct += matched_formulas
                    formula_total += len(fol_list_gt)
        except Exception:
            pass"""

    replacement_content = """        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            if isinstance(parsed_response, list):
                predicted_premises_fol = [str(x).strip() for x in parsed_response]
                all_formulas_valid = True
                for formula in parsed_response:
                    if fol_parser_available:
                        try:
                            is_valid, _ = try_parse_fol(str(formula))
                            if not is_valid:
                                all_formulas_valid = False
                                break
                        except Exception:
                            if not basic_validate_fol(str(formula)):
                                all_formulas_valid = False
                                break
                    else:
                        if not basic_validate_fol(str(formula)):
                            all_formulas_valid = False
                            break
                if all_formulas_valid:
                    syntax_valid_count += 1
                
                if isinstance(fol_list_gt, list):
                    is_exact_match = [str(x).strip() for x in parsed_response] == [str(x).strip() for x in fol_list_gt]
                    if is_exact_match:
                        correct_count += 1
                    else:
                        print(f"\\n[MISMATCH] Example ID: {item.get('example_id', 'N/A')}")
                        if len(parsed_response) == len(fol_list_gt):
                            for idx_p, (nl, gt, pred) in enumerate(zip(nl_list, fol_list_gt, parsed_response), 1):
                                if str(gt).strip() != str(pred).strip():
                                    print(f"  Premise {idx_p}: {nl}")
                                    print(f"    GT:   {gt}")
                                    print(f"    Pred: {pred}")
                        else:
                            print(f"  Length Mismatch: GT={len(fol_list_gt)}, Pred={len(parsed_response)}")
                            print(f"  NL:   {nl_list}")
                            print(f"  GT:   {fol_list_gt}")
                            print(f"  Pred: {parsed_response}")
                    
                    matched_formulas = 0
                    for p_f, g_f in zip(parsed_response, fol_list_gt):
                        if str(p_f).strip() == str(g_f).strip():
                            matched_formulas += 1
                    formula_correct += matched_formulas
                    formula_total += len(fol_list_gt)
            else:
                print(f"\\n[MISMATCH - NOT A LIST] Example ID: {item.get('example_id', 'N/A')}")
                print(f"  NL:   {nl_list}")
                print(f"  GT:   {fol_list_gt}")
                print(f"  Pred: {parsed_response}")
        except Exception as parse_exc:
            print(f"\\n[JSON PARSE FAILED] Example ID: {item.get('example_id', 'N/A')}")
            print(f"  NL:   {nl_list}")
            print(f"  GT:   {fol_list_gt}")
            print(f"  Raw response: {response}")
            print(f"  Error: {parse_exc}")"""

    # We normalize CRLF/LF to ensure strict matching
    source_text_normalized = source_text.replace("\r\n", "\n")
    target_pattern_normalized = target_pattern.replace("\r\n", "\n")
    replacement_content_normalized = replacement_content.replace("\r\n", "\n")
    
    if target_pattern_normalized in source_text_normalized:
        new_source_text = source_text_normalized.replace(target_pattern_normalized, replacement_content_normalized)
        # Convert back to list of lines with original line endings
        helper_cell["source"] = [line + "\n" for line in new_source_text.split("\n")][:-1]
        print("Mismatches printing patch applied successfully.")
    else:
        # Fallback search if exact match fails due to small formatting variations
        print("Warning: Target pattern not found exactly. Attempting line-by-line fallback...")
        # Let's inspect helper cell lines
        for idx, line in enumerate(source_lines):
            if "predicted_premises_fol = []" in line:
                print(f"Found predicted_premises_fol on line {idx}: {line.strip()}")
        # Actually, let's just rewrite evaluate_fol_accuracy fully to be robust
        # Let's read Cell 6 code, find evaluate_fol_accuracy, and replace it.
        # But wait, we already have verify_with_z3, unify_fol_predicates etc. defined there.
        # Let's see: we can look at the current notebook content for evaluate_fol_accuracy.
        
        # Let's check why exact match failed (if it does).
        # We will run the script first to see if it finds the target.
else:
    print("Warning: Helper cell not found.")

with open(ipynb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Finished patching train_folc_kaggle.ipynb!")
