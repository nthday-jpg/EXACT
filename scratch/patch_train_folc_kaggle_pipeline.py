import json
import os
import re

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

print(f"Loading notebook: {notebook_path}...")
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find Cell 6 (contains SFTTrainer, check_sample_with_z3, evaluate_fol_accuracy)
target_cell = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code" and cell.get("id") == "0ece368f":
        target_cell = cell
        break

if not target_cell:
    print("Error: Could not find cell with ID '0ece368f'")
    exit(1)

source_text = "".join(target_cell["source"])

# We want to replace everything from "def check_sample_with_z3(" to the line before "def evaluate_physics_accuracy("
# Let's write the new block to insert.
new_pipeline_block = """# --- SEMANTIC FALLBACK PROMPTS & HELPERS ---
SEMANTIC_YESNO_SYSTEM_PROMPT = (
    "You are a logical reasoning assistant. "
    "Given a set of premises and a conclusion, determine whether the conclusion logically follows from the premises.\\n\\n"
    "STRICT RULES:\\n"
    "- Answer ONLY with one of: Yes, No, or Uncertain.\\n"
    "- 'Yes' means the conclusion is a logical consequence of the premises.\\n"
    "- 'No' means the conclusion contradicts or is inconsistent with the premises.\\n"
    "- 'Uncertain' means the premises do not provide enough information to determine the conclusion.\\n"
    "- Do NOT add any explanation, punctuation, or extra text."
)

SEMANTIC_YESNO_USER_PROMPT_TEMPLATE = (
    "Premises:\\n{premises_text}\\n\\n"
    "Conclusion:\\n{conclusion_nl}\\n\\n"
    "Does the conclusion logically follow from the premises? Answer Yes, No, or Uncertain only."
)

SEMANTIC_MCQ_SYSTEM_PROMPT = (
    "You are a logical reasoning assistant. "
    "Given a set of premises and a multiple-choice question, select the single best answer that logically follows from the premises.\\n\\n"
    "STRICT RULES:\\n"
    "- Answer ONLY with the capital letter of your chosen option (A, B, C, or D).\\n"
    "- Do NOT add any explanation or extra text."
)

SEMANTIC_MCQ_USER_PROMPT_TEMPLATE = (
    "Premises:\\n{premises_text}\\n\\n"
    "Question:\\n{question_nl}\\n\\n"
    "Select the single best answer: respond with ONLY the letter (A, B, C, or D)."
)

def llm_generate_text(model, tokenizer, prompt, system_prompt="", max_new_tokens=15):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

def check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=None):
    from z3 import unsat, sat
    
    # 1. Parse MCQ options
    options = parse_mcq_options(question)
    
    if len(options) >= 2:
        # MCQ flow
        opt_keys = sorted(options.keys())
        opt_texts = [options[k] for k in opt_keys]
        
        # Translate all options to FOL in one batch
        options_fol = translate_sentences(model, tokenizer, opt_texts)
        if len(options_fol) != len(opt_keys):
            # Fallback if mismatch: translate one by one
            options_fol = []
            for opt_text in opt_texts:
                options_fol.append(translate_single_sentence(model, tokenizer, opt_text))
            
        # Unify predicates across both premises and options to prevent sort/predicate name mismatches
        all_fol = predicted_premises_fol + options_fol
        unified_fol = unify_fol_predicates(all_fol)
        unified_premises_fol = unified_fol[:len(predicted_premises_fol)]
        unified_options_fol = unified_fol[len(predicted_premises_fol):]
        
        entailed_options = []
        consistent_options = []
        
        for idx, k in enumerate(opt_keys):
            opt_fol = unified_options_fol[idx] if idx < len(unified_options_fol) else ""
            if not opt_fol:
                continue
            # Check if entailed
            res = verify_with_z3(unified_premises_fol, opt_fol, negate_conclusion=True)
            if res.get("result") == unsat:
                entailed_options.append(k)
            elif res.get("result") == sat:
                # Check if consistent (not contradicted)
                res_neg = verify_with_z3(unified_premises_fol, opt_fol, negate_conclusion=False)
                if res_neg.get("result") != unsat:
                    consistent_options.append(k)
                    
        if len(entailed_options) == 1:
            return entailed_options[0]
        elif len(entailed_options) > 1:
            # Let LLM select the best option among verified candidates
            choices_list = []
            for k in entailed_options:
                choices_list.append(f"{k}. {options[k]}")
            choices_str = "\\n".join(choices_list)
            premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
            prompt = (
                f"You are a logical reasoning assistant.\\n"
                f"Given the premises and the question:\\n\\n"
                f"Premises:\\n{premises_text}\\n\\n"
                f"Question: {question}\\n\\n"
                f"Our formal symbolic prover has verified that the following options are mathematically valid conclusions:\\n"
                f"{choices_str}\\n\\n"
                f"Select the single most appropriate and intended conclusion from the verified options above.\\n"
                f"Respond with ONLY the capital letter (A, B, C, or D) of your choice."
            )
            try:
                best_opt = llm_generate_text(model, tokenizer, prompt, max_new_tokens=5).strip()
                match = re.search(r"\\b([A-D])\\b", best_opt)
                if match and match.group(1) in entailed_options:
                    return match.group(1)
            except Exception:
                pass
            return entailed_options[0]
        elif len(consistent_options) >= 1:
            if len(consistent_options) == 1:
                return consistent_options[0]
            else:
                # Let LLM select the best option among consistent candidates
                choices_str = "\\n".join(f"{k}. {options[k]}" for k in consistent_options)
                premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
                prompt = (
                    f"You are a logical reasoning assistant.\\n"
                    f"Given the premises and the question:\\n\\n"
                    f"Premises:\\n{premises_text}\\n\\n"
                    f"Question: {question}\\n\\n"
                    f"Our formal symbolic prover has verified that the following options are consistent (not contradicted by the premises):\\n"
                    f"{choices_str}\\n\\n"
                    f"Select the single most appropriate and intended conclusion from the consistent options above.\\n"
                    f"Respond with ONLY the capital letter (A, B, C, or D) of your choice."
                )
                try:
                    best_opt = llm_generate_text(model, tokenizer, prompt, max_new_tokens=5).strip()
                    match = re.search(r"\\b([A-D])\\b", best_opt)
                    if match and match.group(1) in consistent_options:
                        return match.group(1)
                except Exception:
                    pass
                return consistent_options[0]
        else:
            # Fallback: Semantic LLM check
            premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
            sem_prompt = SEMANTIC_MCQ_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                question_nl=question
            )
            try:
                sem_resp = llm_generate_text(model, tokenizer, sem_prompt, system_prompt=SEMANTIC_MCQ_SYSTEM_PROMPT, max_new_tokens=10).strip()
                sem_clean = sem_resp.strip("., ")
                if "unknown" in sem_clean.lower():
                    return "Unknown"
                match = re.search(r"\\b([A-D])\\b", sem_clean)
                if match:
                    return match.group(1)
            except Exception:
                pass
            return "Unknown"
            
    else:
        # Yes/No/Uncertain flow
        conclusion_text = strip_question_framing(question)
        conclusion_fol_list = translate_sentences(model, tokenizer, [conclusion_text])
        conclusion_fol = conclusion_fol_list[0] if conclusion_fol_list else ""
        
        if not conclusion_fol:
            # Semantic fallback immediately if translation fails
            premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
            sem_prompt = SEMANTIC_YESNO_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                conclusion_nl=question
            )
            try:
                sem_resp = llm_generate_text(model, tokenizer, sem_prompt, system_prompt=SEMANTIC_YESNO_SYSTEM_PROMPT, max_new_tokens=10).strip()
                sem_lower = sem_resp.lower().strip("., ")
                if sem_lower.startswith("yes"):
                    return "Yes"
                elif sem_lower.startswith("no"):
                    return "No"
            except Exception:
                pass
            return "Unknown"
            
        # Unify predicates across both premises and conclusion
        all_fol = predicted_premises_fol + [conclusion_fol]
        unified_fol = unify_fol_predicates(all_fol)
        unified_premises_fol = unified_fol[:-1]
        unified_conclusion_fol = unified_fol[-1]
        
        # Check entailment of conclusion
        res = verify_with_z3(unified_premises_fol, unified_conclusion_fol, negate_conclusion=True)
        if res.get("result") == unsat:
            return "Yes"
            
        # Check entailment of negation of conclusion
        res_neg = verify_with_z3(unified_premises_fol, unified_conclusion_fol, negate_conclusion=False)
        if res_neg.get("result") == unsat:
            return "No"
            
        # Semantic LLM fallback: Z3 cannot determine entailment — ask the LLM directly
        premises_text = "\\n".join(f"- {p}" for p in (premises_nl or []))
        sem_prompt = SEMANTIC_YESNO_USER_PROMPT_TEMPLATE.format(
            premises_text=premises_text,
            conclusion_nl=question
        )
        try:
            sem_resp = llm_generate_text(model, tokenizer, sem_prompt, system_prompt=SEMANTIC_YESNO_SYSTEM_PROMPT, max_new_tokens=10).strip()
            sem_lower = sem_resp.lower().strip("., ")
            if sem_lower.startswith("yes"):
                return "Yes"
            elif sem_lower.startswith("no"):
                return "No"
        except Exception:
            pass
            
        return "Unknown"

def evaluate_fol_accuracy(model, tokenizer, val_samples, limit=None):
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
                max_new_tokens=1024, # Increased for safety
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        cleaned_response = clean_json_response(response)
        
        predicted_premises_fol = []
        try:
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
            pass
            
        # Downstream Z3 Question Answering Accuracy evaluation
        question = item.get("question", "")
        gt_answer = item.get("answer", "")
        if question and gt_answer and predicted_premises_fol:
            z3_total_count += 1
            try:
                pred_ans = check_sample_with_z3(predicted_premises_fol, question, model, tokenizer, premises_nl=nl_list)
                if check_answers_match(pred_ans, gt_answer):
                    z3_correct_count += 1
                
                # Debug output for first sample
                if total_count < 2:
                    print(f"\\n--- Z3 QA Evaluation Sample {total_count + 1} ---")
                    print(f"Question: {question}")
                    print(f"GT Answer: {gt_answer} | Z3 Predicted Answer: {pred_ans}")
                    print(f"Predicted FOL: {predicted_premises_fol}")
                    print("-" * 30)
            except Exception as z3_err:
                if total_count < 2:
                    print(f"Z3 Evaluation Error for Sample {total_count + 1}: {z3_err}")
                    
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
    return em_acc, json_rate, syntax_rate

"""

# Find where check_sample_with_z3 starts
start_pattern = "def check_sample_with_z3("
end_pattern = "def evaluate_physics_accuracy("

start_idx = source_text.find(start_pattern)
end_idx = source_text.find(end_pattern)

if start_idx == -1 or end_idx == -1:
    print(f"Error: Could not locate boundaries in source_text. start_idx={start_idx}, end_idx={end_idx}")
    exit(1)

# Replace target block
updated_source_text = source_text[:start_idx] + new_pipeline_block + source_text[end_idx:]

# Split back to lines, preserving exact format (each line must end with \n)
lines = [line + "\n" for line in updated_source_text.split("\n")]
if lines and lines[-1] == "\n":
    lines.pop()

target_cell["source"] = lines

# Save back to notebook
with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Successfully patched logic pipeline and evaluate_fol_accuracy in notebook!")
