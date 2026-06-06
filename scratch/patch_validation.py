import json

notebook_path = r"d:\mduy\source\repos\EXACT\src\llm\tuning\train_folc_kaggle.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find the cell containing "# 6. Configure SFTTrainer and start training"
target_cell = None
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "# 6. Configure SFTTrainer and start training" in source:
            target_cell = cell
            break

if target_cell is None:
    print("Could not find the target SFTTrainer configuration cell in the notebook.")
    exit(1)

# Multi-line string with the new cell content
cell_content = """# 6. Configure SFTTrainer and start training
import os
import glob
import torch
import json
import random
from trl import SFTTrainer, SFTConfig
from transformers import TrainerCallback, DataCollatorForLanguageModeling
from typing import Dict, Union, Any, Optional, List, Tuple

class LossLoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is not None:
            if "loss" in logs:
                print(f"Step {state.global_step}: training_loss = {logs['loss']:.6f}")
            if "eval_loss" in logs:
                print(f"Step {state.global_step}: validation_loss = {logs['eval_loss']:.6f}")

class CustomDataCollator(DataCollatorForLanguageModeling):
    def __init__(self, response_template, tokenizer, *args, **kwargs):
        super().__init__(tokenizer=tokenizer, mlm=False, *args, **kwargs)
        self.response_template = response_template
        self.response_token_ids = self.tokenizer.encode(self.response_template, add_special_tokens=False)
        
    def __call__(self, examples):
        batch = super().__call__(examples)
        labels = batch["labels"]
        for i in range(labels.size(0)):
            input_ids = batch["input_ids"][i].tolist()
            response_idx = -1
            n_template = len(self.response_token_ids)
            for j in range(len(input_ids) - n_template + 1):
                if input_ids[j:j+n_template] == self.response_token_ids:
                    response_idx = j + n_template
                    break
            
            if response_idx != -1:
                labels[i, :response_idx] = -100
                
        return batch

# --- ACCURACY EVALUATION HELPERS ---
def compare_physics_answers(pred_ans, pred_unit, gt_ans, gt_unit):
    if pred_ans is None or gt_ans is None:
        return False
    if not isinstance(pred_ans, list):
        pred_ans = [pred_ans]
    if not isinstance(gt_ans, list):
        gt_ans = [gt_ans]
    if len(pred_ans) != len(gt_ans):
        return False
    for p_val, g_val in zip(pred_ans, gt_ans):
        try:
            p_num = float(p_val)
            g_num = float(g_val)
            if g_num == 0.0:
                if abs(p_num) >= 1e-5:
                    return False
            else:
                rel_err = abs(p_num - g_num) / abs(g_num)
                if rel_err > 0.02:  # 2% tolerance
                    return False
        except (ValueError, TypeError):
            if str(p_val).strip().lower() != str(g_val).strip().lower():
                return False
    return True

def basic_validate_fol(formula: str) -> bool:
    # Check basic parentheses balance
    if formula.count("(") != formula.count(")"):
        return False
    # Check that forbidden operators or lowercase operators aren't used incorrectly
    for bad in [" and ", " or ", " not "]:
        if bad in formula:
            return False
    # Check that quantifiers have correct casing
    for bad_q in ["forall(", "exists("]:
        if bad_q in formula.lower() and not (bad_q.capitalize() in formula or "ForAll" in formula or "Exists" in formula):
            return False
    return True

def evaluate_fol_accuracy(model, tokenizer, val_samples, limit=50):
    print(f"Evaluating FOL Accuracy on {min(len(val_samples), limit)} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    syntax_valid_count = 0
    formula_correct = 0
    formula_total = 0
    
    try:
        from src.logic.reasoning.parser import try_parse_fol
        fol_parser_available = True
    except ImportError:
        fol_parser_available = False
        print("Warning: Z3 or logic parser not available. Using basic syntax checking (parentheses/operators).")
    
    # Shuffle and sample to keep evaluation fast
    random_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    
    for item in random_subset:
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
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        try:
            parsed_response = json.loads(response)
            valid_json_count += 1
            if isinstance(parsed_response, list):
                # Check syntax validity of each formula
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
                    # Sample level exact match
                    if [str(x).strip() for x in parsed_response] == [str(x).strip() for x in fol_list_gt]:
                        correct_count += 1
                    
                    # Formula level accuracy
                    matched_formulas = 0
                    for p_f, g_f in zip(parsed_response, fol_list_gt):
                        if str(p_f).strip() == str(g_f).strip():
                            matched_formulas += 1
                    formula_correct += matched_formulas
                    formula_total += len(fol_list_gt)
        except Exception:
            pass
        total_count += 1
        
    em_acc = (correct_count / total_count) * 100 if total_count > 0 else 0
    formula_acc = (formula_correct / formula_total) * 100 if formula_total > 0 else 0
    json_rate = (valid_json_count / total_count) * 100 if total_count > 0 else 0
    syntax_rate = (syntax_valid_count / total_count) * 100 if total_count > 0 else 0
    
    print("\\n=== FOL Evaluation Metrics ===")
    print(f"FOL Exact Match Accuracy (Sample Level): {em_acc:.2f}% ({correct_count}/{total_count})")
    print(f"FOL Formula Level Match Accuracy: {formula_acc:.2f}% ({formula_correct}/{formula_total})")
    print(f"FOL Syntax Validity Rate: {syntax_rate:.2f}% ({syntax_valid_count}/{total_count})")
    print(f"FOL JSON Validity Rate: {json_rate:.2f}% ({valid_json_count}/{total_count})")
    return em_acc, json_rate, syntax_rate

def evaluate_physics_accuracy(model, tokenizer, val_samples, limit=50):
    print(f"Evaluating Physics Accuracy on {min(len(val_samples), limit)} samples...")
    correct_count = 0
    total_count = 0
    valid_json_count = 0
    python_syntax_count = 0
    exec_count = 0
    
    random_subset = random.Random(42).sample(val_samples, min(len(val_samples), limit))
    
    for item in random_subset:
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
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        try:
            parsed_response = json.loads(response)
            valid_json_count += 1
            code_str = parsed_response.get("python_code", "")
            
            # Extract ground truth python code from output string
            try:
                gt_parsed = json.loads(gt_output_str)
                gt_code_str = gt_parsed.get("python_code", "")
            except Exception:
                gt_code_str = ""
                
            if code_str:
                # Check Python Syntax Validity (compiles successfully)
                try:
                    compile(code_str, "<string>", "exec")
                    python_syntax_count += 1
                except Exception:
                    pass

                if gt_code_str:
                    local_vars_pred = {}
                    local_vars_gt = {}
                    try:
                        import sympy as sp
                        # Execute predicted code
                        exec(code_str, {"sp": sp}, local_vars_pred)
                        pred_ans = local_vars_pred.get("ans", None)
                        pred_unit = local_vars_pred.get("unit", None)
                        
                        # Execute ground truth code
                        exec(gt_code_str, {"sp": sp}, local_vars_gt)
                        gt_ans = local_vars_gt.get("ans", None)
                        gt_unit = local_vars_gt.get("unit", None)
                        
                        if pred_ans is not None and gt_ans is not None:
                            exec_count += 1
                            if compare_physics_answers(pred_ans, pred_unit, gt_ans, gt_unit):
                                correct_count += 1
                    except Exception:
                        pass
        except Exception:
            pass
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
    return acc, json_rate, python_syntax_rate, exec_rate

def train_model(train_dataset, val_dataset, output_dir):
    clean_memory()
    
    # Mathematically exact, dynamic warmup steps calculation based on actual dataset size
    num_samples = len(train_dataset)
    effective_batch_size = BATCH_SIZE * GRADIENT_ACCUMULATION
    steps_per_epoch = num_samples // effective_batch_size
    if num_samples % effective_batch_size != 0:
        steps_per_epoch += 1
    total_steps = steps_per_epoch * EPOCHS
    
    # Target exactly 5% warmup steps of total training steps (HF v5.2 compliant integer steps)
    warmup_steps = max(1, int(total_steps * 0.05))
    print(f"Training on {num_samples} samples. Steps per epoch: {steps_per_epoch}. Total steps: {total_steps}. Dynamic warmup steps: {warmup_steps}")
    
    base_model = load_base_model()
    
    # Resume from previous checkpoints if adapter_config.json exists in output_dir
    adapter_config_path = os.path.join(output_dir, "adapter_config.json")
    if os.path.exists(adapter_config_path):
        print(f"Resuming PEFT adapter weights from {output_dir}...")
        model = PeftModel.from_pretrained(base_model, output_dir, is_trainable=True)
    else:
        print("Initializing a new PEFT adapter...")
        model = get_peft_model(base_model, peft_config)
        
    model.print_trainable_parameters()
    
    # Highly Optimized SFTConfig with Cosine Decay Scheduler & Warmup
    sft_config = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        lr_scheduler_type="cosine",             # Cosine learning rate decay scheduler
        warmup_steps=warmup_steps,              # Compliant, dynamic warm-up steps to stabilize updates
        fp16=use_fp16,
        bf16=use_bf16,
        logging_steps=1,
        logging_first_step=True,
        optim="adamw_torch",
        gradient_checkpointing=GRADIENT_CHECKPOINTING,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        per_device_eval_batch_size=BATCH_SIZE,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=2,
        dataset_text_field="text",
        max_length=MAX_LENGTH,
        neftune_noise_alpha=None,
        dataloader_num_workers=2,
        dataloader_pin_memory=True
    )

    response_template = "<|im_start|>assistant\\n"
    collator = CustomDataCollator(
        response_template=response_template, 
        tokenizer=tokenizer
    )
    
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        args=sft_config,
        data_collator=collator,
        callbacks=[LossLoggingCallback()]
    )

    checkpoints = glob.glob(os.path.join(output_dir, "checkpoint-*"))
    resume_path = None
    if checkpoints:
        checkpoints.sort(key=lambda x: int(x.split("-")[-1]))
        resume_path = checkpoints[-1]
        print(f"Found checkpoints. Resuming training from: {resume_path}")
        
    trainer.train(resume_from_checkpoint=resume_path)
    
    print(f"Saving best validation adapter weights and tokenizer to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Training completed successfully!")
    
    # --- POST-TRAINING ACCURACY EVALUATION ---
    try:
        print("\\n=== Starting Post-Training Accuracy Evaluation ===")
        model.eval()
        evaluate_fol_accuracy(model, tokenizer, val_fol, limit=50)
        evaluate_physics_accuracy(model, tokenizer, val_physics, limit=50)
    except Exception as e:
        print(f"Error during post-training evaluation: {e}")
    
    # Clean up model & trainer from memory
    del trainer
    del model
    del base_model
    clean_memory()
"""

# Split by newline and add the newline back as expected by Jupyter notebook format
target_cell["source"] = [line + "\n" for line in cell_content.splitlines()]
# Strip trailing newline character from the very last line to prevent extra empty line
if target_cell["source"] and target_cell["source"][-1].endswith("\n"):
    target_cell["source"][-1] = target_cell["source"][-1][:-1]

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Successfully patched train_folc_kaggle.ipynb!")
