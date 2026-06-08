import json
import os
import re

# New implementation of clean_json_response with corrected single backslash regex
NEW_CLEAN_JSON = """def clean_json_response(response: str) -> str:
    response = response.strip()
    if response.startswith("```"):
        match = re.search(r"```(?:json)?\\s*(.*?)\\s*```", response, re.DOTALL)
        if match:
            response = match.group(1).strip()
            
    first_brace = response.find("{")
    first_bracket = response.find("[")
    
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        obj_match = re.search(r"(\\{.*\\})", response, re.DOTALL)
        if obj_match:
            response = obj_match.group(1).strip()
        else:
            obj_match_open = re.search(r"(\\{.*)", response, re.DOTALL)
            if obj_match_open:
                response = obj_match_open.group(1).strip()
    elif first_bracket != -1:
        array_match = re.search(r"(\\[.*\\])", response, re.DOTALL)
        if array_match:
            response = array_match.group(1).strip()
        else:
            array_match_open = re.search(r"(\\[.*)", response, re.DOTALL)
            if array_match_open:
                response = array_match_open.group(1).strip()
                
    in_quote = False
    escape = False
    stack = []
    i = 0
    while i < len(response):
        char = response[i]
        if escape:
            escape = False
        elif char == '\\\\':
            escape = True
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote:
            if char in ('{', '['):
                stack.append(char)
            elif char in ('}', ']'):
                if stack and ((char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '[')):
                    stack.pop()
        i += 1
        
    if in_quote:
        response += '"'
    while stack:
        top = stack.pop()
        if top == '{':
            response += '}'
        elif top == '[':
            response += ']'
            
    return response"""

# New implementation of evaluate_fol_accuracy that outputs failure cases to a file
NEW_EVALUATE_FOL = """def evaluate_fol_accuracy(model, tokenizer, val_samples, limit=None):
    eval_limit = limit if limit is not None else len(val_samples)
    print(f"Evaluating FOL Accuracy on {eval_limit} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    syntax_valid_count = 0
    formula_correct = 0
    formula_total = 0
    
    z3_correct_count = 0
    z3_total_count = 0
    
    failed_cases = []
    
    if limit is not None:
        eval_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    else:
        eval_subset = val_samples
    
    for item in eval_subset:
        nl_list = item["premises-NL"]
        fol_list_gt = item["premises-FOL"]
        
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\\n"
            
        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt.strip()}
        ]
        
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        cleaned_response = ""
        try:
            cleaned_response = clean_json_response(response)
        except Exception as e:
            cleaned_response = response
            
        predicted_premises_fol = []
        is_json_valid = False
        is_syntax_valid = False
        is_exact_match = False
        
        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            is_json_valid = True
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
                    is_syntax_valid = True
                
                if isinstance(fol_list_gt, list):
                    if [str(x).strip() for x in parsed_response] == [str(x).strip() for x in fol_list_gt]:
                        correct_count += 1
                        is_exact_match = True
                    
                    matched_formulas = 0
                    for p_f, g_f in zip(parsed_response, fol_list_gt):
                        if str(p_f).strip() == str(g_f).strip():
                            matched_formulas += 1
                    formula_correct += matched_formulas
                    formula_total += len(fol_list_gt)
        except Exception:
            pass
            
        question = item.get("question", "")
        gt_answer = item.get("answer", "")
        pred_ans = "N/A"
        is_qa_correct = False
        
        if question and gt_answer and predicted_premises_fol:
            z3_total_count += 1
            try:
                pred_ans = check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=nl_list)
                if check_answers_match(pred_ans, gt_answer):
                    z3_correct_count += 1
                    is_qa_correct = True
                
                if total_count < 2:
                    print(f"\\n--- Z3 QA Evaluation Sample {total_count + 1} ---")
                    print(f"Question: {question}")
                    print(f"GT Answer: {gt_answer} | Z3 Predicted Answer: {pred_ans}")
                    print(f"Predicted FOL: {predicted_premises_fol}")
                    print("-" * 30)
            except Exception as z3_err:
                if total_count < 2:
                    print(f"Z3 Evaluation Error for Sample {total_count + 1}: {z3_err}")
                    
        # Track failure cases
        if not is_exact_match or not is_syntax_valid or (question and not is_qa_correct):
            failed_cases.append({
                "example_id": item.get("example_id", ""),
                "premises-NL": nl_list,
                "premises-FOL-GT": fol_list_gt,
                "premises-FOL-Pred": predicted_premises_fol,
                "raw_response": response,
                "cleaned_response": cleaned_response,
                "question": question,
                "answer-GT": gt_answer,
                "answer-Pred": pred_ans,
                "is_json_valid": is_json_valid,
                "is_syntax_valid": is_syntax_valid,
                "is_exact_match": is_exact_match,
                "is_qa_correct": is_qa_correct
            })
            
        total_count += 1
        
    em_acc = (correct_count / total_count) * 100 if total_count > 0 else 0
    formula_acc = (formula_correct / formula_total) * 100 if formula_total > 0 else 0
    json_rate = (valid_json_count / total_count) * 100 if total_count > 0 else 0
    syntax_rate = (syntax_valid_count / total_count) * 100 if total_count > 0 else 0
    z3_acc = (z3_correct_count / z3_total_count) * 100 if z3_total_count > 0 else 0
    
    print("\\n=== FOL Evaluation Metrics ===")
    print(f"FOL Exact Match Accuracy (Sample Level): {em_acc:.2f}% ({correct_count}/{total_count})")
    print(f"FOL Formula Level Match Accuracy: {formula_acc:.2f}% ({formula_correct}/{formula_total})")
    print(f"FOL Syntax Validity Rate: {syntax_rate:.2f}% ({syntax_valid_count}/{total_count})")
    print(f"FOL JSON Validity Rate: {json_rate:.2f}% ({valid_json_count}/{total_count})")
    print(f"FOL Z3 Downstream QA Accuracy: {z3_acc:.2f}% ({z3_correct_count}/{z3_total_count})")
    
    # Save failure cases to a file
    output_failed_path = "fol_failed_cases.json"
    try:
        with open(output_failed_path, "w", encoding="utf-8") as f_out:
            json.dump(failed_cases, f_out, indent=2, ensure_ascii=False)
        print(f"Saved {len(failed_cases)} failed cases to: {os.path.abspath(output_failed_path)}")
    except Exception as save_err:
        print(f"Error saving failed cases: {save_err}")
        
    return em_acc, json_rate, syntax_rate"""

def patch_notebook(nb_path):
    print(f"Patching notebook: {nb_path}")
    if not os.path.exists(nb_path):
        print(f"Error: Notebook {nb_path} does not exist.")
        return False
        
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    patched = False
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
            
        cell_source = "".join(cell.get("source", []))
        if "def evaluate_fol_accuracy" in cell_source:
            print(f"  Found target cell at index {cell_idx}")
            
            # Use regex to replace def clean_json_response(response: str) -> str: ... return response
            # Let's find def clean_json_response and def evaluate_fol_accuracy in the source code
            # We will split by function names and replace them cleanly
            source_str = cell_source
            
            # Replace clean_json_response
            # Look for def clean_json_response up to return response
            clean_pattern = r"def clean_json_response\(response:\s*str\)\s*->\s*str:.*?return response"
            if re.search(clean_pattern, source_str, re.DOTALL):
                source_str = re.sub(clean_pattern, lambda m: NEW_CLEAN_JSON, source_str, flags=re.DOTALL)
                print("    Successfully replaced clean_json_response")
            else:
                print("    Warning: Could not match clean_json_response pattern")
                
            # Replace evaluate_fol_accuracy
            # Look for def evaluate_fol_accuracy up to return em_acc, json_rate, syntax_rate
            eval_pattern = r"def evaluate_fol_accuracy\(model,\s*tokenizer,\s*val_samples,\s*limit=None\):.*?return em_acc,\s*json_rate,\s*syntax_rate"
            if re.search(eval_pattern, source_str, re.DOTALL):
                source_str = re.sub(eval_pattern, lambda m: NEW_EVALUATE_FOL, source_str, flags=re.DOTALL)
                print("    Successfully replaced evaluate_fol_accuracy")
            else:
                print("    Warning: Could not match evaluate_fol_accuracy pattern")
                
            # Split back into lines with newlines
            lines = [line + "\n" for line in source_str.split("\n")]
            # Strip trailing newline from last line if it's empty
            if lines and lines[-1] == "\n":
                lines.pop()
            # Remove newline from the actual final line if needed
            if lines:
                lines[-1] = lines[-1].rstrip("\n")
                
            cell["source"] = lines
            patched = True
            break
            
    if patched:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"  Successfully saved patched notebook: {nb_path}")
        return True
    else:
        print(f"  Failed to patch notebook: {nb_path} (target cell not found)")
        return False

def main():
    patch_notebook("src/llm/tuning/fol.ipynb")
    patch_notebook("src/llm/tuning/fol_and_physics.ipynb")

if __name__ == "__main__":
    main()
