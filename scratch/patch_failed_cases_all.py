import json
import os
import re

NEW_EVALUATE_PHYSICS = """def evaluate_physics_accuracy(model, tokenizer, val_samples, limit=None):
    eval_limit = limit if limit is not None else len(val_samples)
    print(f"Evaluating Physics Accuracy on {eval_limit} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    python_syntax_count = 0
    exec_count = 0
    
    failed_cases = []
    
    if limit is not None:
        eval_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    else:
        eval_subset = val_samples
        
    for item in eval_subset:
        inp = item["input"]
        gt_output_str = item["output"]
        
        messages = [
            {"role": "system", "content": physics_system_prompt},
            {"role": "user", "content": inp.strip()}
        ]
        
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        cleaned_response = clean_json_response(response)
        
        is_json_valid = False
        is_syntax_valid = False
        is_executed = False
        is_correct = False
        pred_ans = None
        pred_unit = None
        gt_ans = None
        gt_unit = None
        
        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            is_json_valid = True
            code_str = parsed_response.get("python_code", "")
            
            try:
                gt_parsed = json.loads(gt_output_str)
                gt_code_str = gt_parsed.get("python_code", "")
            except Exception:
                gt_code_str = ""
                
            if code_str:
                try:
                    compile(code_str, "<string>", "exec")
                    python_syntax_count += 1
                    is_syntax_valid = True
                except Exception:
                    pass
                    
                if gt_code_str:
                    local_vars_pred = {}
                    local_vars_gt = {}
                    try:
                        import sympy as sp
                        exec(code_str, {"sp": sp}, local_vars_pred)
                        pred_ans = local_vars_pred.get("ans", None)
                        pred_unit = local_vars_pred.get("unit", None)
                        
                        exec(gt_code_str, {"sp": sp}, local_vars_gt)
                        gt_ans = local_vars_gt.get("ans", None)
                        gt_unit = local_vars_gt.get("unit", None)
                        
                        if pred_ans is not None and gt_ans is not None:
                            exec_count += 1
                            is_executed = True
                            if compare_physics_answers(pred_ans, pred_unit, gt_ans, gt_unit):
                                correct_count += 1
                                is_correct = True
                    except Exception:
                        pass
        except Exception:
            pass
            
        if not is_correct:
            failed_cases.append({
                "input": inp,
                "output_gt": gt_output_str,
                "raw_response": response,
                "cleaned_response": cleaned_response,
                "pred_ans": pred_ans,
                "pred_unit": pred_unit,
                "gt_ans": gt_ans,
                "gt_unit": gt_unit,
                "is_json_valid": is_json_valid,
                "is_syntax_valid": is_syntax_valid,
                "is_executed": is_executed
            })
        total_count += 1
        
    acc = (correct_count / total_count) * 100 if total_count > 0 else 0
    json_rate = (valid_json_count / total_count) * 100 if total_count > 0 else 0
    python_syntax_rate = (python_syntax_count / total_count) * 100 if total_count > 0 else 0
    exec_rate = (exec_count / total_count) * 100 if total_count > 0 else 0
    
    print("\\n=== Physics Evaluation Metrics ===")
    print(f"Physics Accuracy: {acc:.2f}% ({correct_count}/{total_count})")
    print(f"Physics JSON Validity Rate: {json_rate:.2f}% ({valid_json_count}/{total_count})")
    print(f"Physics Python Syntax Validity Rate: {python_syntax_rate:.2f}% ({python_syntax_count}/{total_count})")
    print(f"Physics Code Execution Rate: {exec_rate:.2f}% ({exec_count}/{total_count})")
    
    # Save failure cases to a file
    output_failed_path = "physics_failed_cases.json"
    class SympyEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                import sympy as sp
                if isinstance(obj, sp.Basic):
                    try:
                        val = float(obj.evalf())
                        return int(val) if val.is_integer() else val
                    except Exception:
                        return str(obj)
            except Exception:
                pass
            if isinstance(obj, set):
                return list(obj)
            try:
                return super().default(obj)
            except TypeError:
                return str(obj)

    try:
        with open(output_failed_path, "w", encoding="utf-8") as f_out:
            json.dump(failed_cases, f_out, indent=2, ensure_ascii=False, cls=SympyEncoder)
        print(f"Saved {len(failed_cases)} failed cases to: {os.path.abspath(output_failed_path)}")
    except Exception as save_err:
        print(f"Error saving failed cases: {save_err}")
        
    return acc, json_rate, python_syntax_rate, exec_rate"""

NEW_EVALUATE_ROUTER = """def evaluate_router_accuracy(model, tokenizer, val_samples, limit=None):
    eval_limit = limit if limit is not None else len(val_samples)
    print(f"Evaluating Router Accuracy on {eval_limit} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    domain_exact_match_count = 0
    multi_state_correct_count = 0
    
    failed_cases = []
    
    if limit is not None:
        eval_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    else:
        eval_subset = val_samples
        
    for item in eval_subset:
        inp = item["input"]
        gt_output_str = item["output"]
        
        messages = [
            {"role": "system", "content": router_system_prompt},
            {"role": "user", "content": f"<QUESTION>\\n{inp.strip()}\\n</QUESTION>"}
        ]
        
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        cleaned_response = clean_json_response(response)
        
        is_json_valid = False
        is_correct = False
        pred_domains = []
        gt_domains = []
        pred_multi_state = False
        gt_multi_state = False
        
        try:
            parsed_response = json.loads(cleaned_response)
            valid_json_count += 1
            is_json_valid = True
            
            # Ground truth
            gt_parsed = json.loads(gt_output_str)
            
            pred_domains = parsed_response.get("domains", [])
            gt_domains = gt_parsed.get("domains", [])
            
            pred_multi_state = parsed_response.get("multi_state", False)
            gt_multi_state = gt_parsed.get("multi_state", False)
            
            domain_exact_match = sorted(pred_domains) == sorted(gt_domains)
            if domain_exact_match:
                domain_exact_match_count += 1
                
            multi_state_correct = bool(pred_multi_state) == bool(gt_multi_state)
            if multi_state_correct:
                multi_state_correct_count += 1
                
            if domain_exact_match and multi_state_correct:
                correct_count += 1
                is_correct = True
        except Exception:
            pass
            
        if not is_correct:
            failed_cases.append({
                "input": inp,
                "output_gt": gt_output_str,
                "raw_response": response,
                "cleaned_response": cleaned_response,
                "pred_domains": pred_domains,
                "gt_domains": gt_domains,
                "pred_multi_state": pred_multi_state,
                "gt_multi_state": gt_multi_state,
                "is_json_valid": is_json_valid
            })
            
        total_count += 1
        
    acc = (correct_count / total_count) * 100 if total_count > 0 else 0
    json_rate = (valid_json_count / total_count) * 100 if total_count > 0 else 0
    domain_acc = (domain_exact_match_count / total_count) * 100 if total_count > 0 else 0
    multi_state_acc = (multi_state_correct_count / total_count) * 100 if total_count > 0 else 0
    
    print("\\n=== Router Evaluation Metrics ===")
    print(f"Router Exact Match Accuracy: {acc:.2f}% ({correct_count}/{total_count})")
    print(f"Router JSON Validity Rate: {json_rate:.2f}% ({valid_json_count}/{total_count})")
    print(f"Router Domain Exact Match Rate: {domain_acc:.2f}% ({domain_exact_match_count}/{total_count})")
    print(f"Router Multi-State Accuracy: {multi_state_acc:.2f}% ({multi_state_correct_count}/{total_count})")
    
    # Save failure cases to a file
    output_failed_path = "router_failed_cases.json"
    class SympyEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                import sympy as sp
                if isinstance(obj, sp.Basic):
                    try:
                        val = float(obj.evalf())
                        return int(val) if val.is_integer() else val
                    except Exception:
                        return str(obj)
            except Exception:
                pass
            if isinstance(obj, set):
                return list(obj)
            try:
                return super().default(obj)
            except TypeError:
                return str(obj)

    try:
        with open(output_failed_path, "w", encoding="utf-8") as f_out:
            json.dump(failed_cases, f_out, indent=2, ensure_ascii=False, cls=SympyEncoder)
        print(f"Saved {len(failed_cases)} failed cases to: {os.path.abspath(output_failed_path)}")
    except Exception as save_err:
        print(f"Error saving failed cases: {save_err}")
        
    return acc, json_rate, domain_acc, multi_state_acc"""

def patch_notebook(nb_path):
    print(f"Processing notebook: {nb_path}")
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
        cell_patched = False
        
        # Check if evaluate_physics_accuracy is in cell source
        if "def evaluate_physics_accuracy" in cell_source:
            # Let's search and replace evaluate_physics_accuracy
            eval_pattern = r"def evaluate_physics_accuracy\(model,\s*tokenizer,\s*val_samples,\s*limit=None\):.*?return acc,\s*json_rate,\s*python_syntax_rate,\s*exec_rate"
            if re.search(eval_pattern, cell_source, re.DOTALL):
                cell_source = re.sub(eval_pattern, lambda m: NEW_EVALUATE_PHYSICS, cell_source, flags=re.DOTALL)
                print("  Successfully replaced evaluate_physics_accuracy")
                cell_patched = True
                patched = True
            else:
                print("  Warning: evaluate_physics_accuracy found but pattern not matched")
                
        # Check if evaluate_router_accuracy is in cell source
        if "def evaluate_router_accuracy" in cell_source:
            # Let's search and replace evaluate_router_accuracy
            eval_pattern = r"def evaluate_router_accuracy\(model,\s*tokenizer,\s*val_samples,\s*limit=None\):.*?return acc,\s*json_rate,\s*domain_acc,\s*multi_state_acc"
            if re.search(eval_pattern, cell_source, re.DOTALL):
                cell_source = re.sub(eval_pattern, lambda m: NEW_EVALUATE_ROUTER, cell_source, flags=re.DOTALL)
                print("  Successfully replaced evaluate_router_accuracy")
                cell_patched = True
                patched = True
            else:
                print("  Warning: evaluate_router_accuracy found but pattern not matched")
                
        # Fix the pre-existing syntax error where else loss and def train_model got concatenated
        if "lossdef train_model" in cell_source:
            cell_source = cell_source.replace("lossdef train_model", "loss\n\ndef train_model")
            print("  Successfully fixed pre-existing syntax error lossdef train_model")
            cell_patched = True
            patched = True
            
        if cell_patched:
            # Split back into lines with newlines using actual newlines
            lines = [line + "\n" for line in cell_source.split("\n")]
            # Strip trailing newline from last line if it's empty
            if lines and lines[-1] == "\n":
                lines.pop()
            # Remove newline from the actual final line if needed
            if lines:
                lines[-1] = lines[-1].rstrip("\n")
            cell["source"] = lines

    if patched:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        print(f"Saved patched notebook: {nb_path}")
        return True
    else:
        print(f"No changes made to {nb_path}")
        return False

def main():
    notebooks = [
        "src/llm/tuning/fol.ipynb",
        "src/llm/tuning/physics.ipynb",
        "src/llm/tuning/fol_and_physics.ipynb",
        "src/llm/tuning/fol_and_router.ipynb",
        "src/llm/tuning/router_and_physics.ipynb"
    ]
    for nb in notebooks:
        patch_notebook(nb)

if __name__ == "__main__":
    main()
