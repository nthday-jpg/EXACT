import json
import os
import sys
import time
import re
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
z3.set_param('proof', False)

from src.logic.pipeline import detect_question_type, parse_mcq_options
from src.logic.translation.pipeline import NLToFOLPipeline
from src.utils.normalization import unify_fol_predicates, normalize_logic_fol_entry
from src.logic.reasoning.verifier import verify_with_z3
from src.llm.llm_client import LLMClient

def normalize_ans(ans):
    if isinstance(ans, list):
        return sorted([normalize_ans(x) for x in ans])
    ans_str = str(ans).strip().lower()
    if ans_str in ("yes", "true"):
        return "yes"
    if ans_str in ("no", "false"):
        return "no"
    if ans_str in ("uncertain", "unknown"):
        return "uncertain"
    return ans_str

def compare_answers(correct, predicted) -> bool:
    return normalize_ans(correct) == normalize_ans(predicted)

def translate_list_with_retry(pipeline, nl_list, glossary_str=None):
    retries = 5
    for attempt in range(retries):
        try:
            res = pipeline.translate_list(nl_list, glossary_str=glossary_str)
            if res and len(res) == len(nl_list):
                return res
        except Exception as e:
            print(f"  -> Translation attempt {attempt+1} failed: {e}")
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                print("  -> Hit rate limit (429). Sleeping 60s...")
                time.sleep(60.0)
            elif "503" in err_str or "overloaded" in err_str or "demand" in err_str or "unavailable" in err_str:
                print("  -> Service unavailable (503). Sleeping 10s...")
                time.sleep(10.0)
            else:
                time.sleep(5.0)
    # If all retries failed, fallback to translating without glossary
    try:
        res = pipeline.translate_list(nl_list)
        if res and len(res) == len(nl_list):
            return res
    except Exception:
        pass
    return [""] * len(nl_list)

def evaluate_val_set():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)

    augmented_path = root / "data" / "processed" / "logic_merged_valid_augmented.json"
    if not augmented_path.exists():
        print(f"Error: {augmented_path} not found.")
        return
        
    with open(augmented_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    val_samples = [item for item in data if item.get("split") == "val"]
    print(f"Loaded {len(val_samples)} validation samples.")
    
    # Initialize translation pipeline using Gemini
    client = LLMClient(
        use_local=False,
        model_name="gemini-3.1-flash-lite",
        temperature=0.1
    )
    pipeline = NLToFOLPipeline(use_local=False, llm_client=client)

    matches = 0
    mismatches = 0
    errors = 0
    results = []
    
    start_time = time.time()
    last_request_time = 0.0
    
    for idx, item in enumerate(val_samples, 1):
        example_id = item.get("example_id")
        premises_fol_raw = item.get("premises-FOL", [])
        premises_nl = item.get("premises-NL", [])
        question = item.get("question", "")
        gt_answer = item.get("answer", "")
        explanation = item.get("explanation", "")
        
        print(f"\n--- [{idx}/{len(val_samples)}] Sample {example_id} ---")
        print(f"Premises (NL):\n" + "\n".join(f"  - {p}" for p in premises_nl))
        print(f"Question: {question}")
        print(f"Ground Truth Answer: {gt_answer}")
        
        # Normalize premises FOL
        premises_fol = [normalize_logic_fol_entry(fol) for fol in premises_fol_raw]
        
        # Detect question type
        q_type = detect_question_type(question)
        options = parse_mcq_options(question)
        
        # Build glossary from premises to guide the question translation
        glossary_str = pipeline.extract_glossary_from_fol(premises_fol)
        
        # Force rate limiting spacing (5.0s per request to stay under 15 RPM)
        elapsed = time.time() - last_request_time
        if elapsed < 5.0:
            time.sleep(5.0 - elapsed)
        
        try:
            last_request_time = time.time()
            if q_type in ("single_choice", "multiple_choice") or len(options) >= 2:
                # MCQ flow
                opt_keys = sorted(options.keys())
                opt_texts = [options[k] for k in opt_keys]
                
                # Translate options under glossary constraints with retry
                options_fol_raw = translate_list_with_retry(pipeline, opt_texts, glossary_str=glossary_str)
                
                # Unify predicates across premises and options
                all_fol = premises_fol + options_fol_raw
                all_fol_unified = unify_fol_predicates(all_fol)
                
                unified_premises = all_fol_unified[:len(premises_fol)]
                unified_options = all_fol_unified[len(premises_fol):]
                options_fol = {k: unified_options[i] for i, k in enumerate(opt_keys)}
                
                print(f"Unified premises FOL:\n" + "\n".join(f"  - {p}" for p in unified_premises))
                print(f"Unified options FOL:")
                for k in opt_keys:
                    print(f"  - {k}: {options_fol[k]}")
                
                # Verify options
                unsat_candidates = []
                consistent_candidates = []
                for k in opt_keys:
                    opt_fol = options_fol.get(k, "")
                    if not opt_fol:
                        continue
                    # 1. Check if entailed
                    verif = verify_with_z3(unified_premises, opt_fol, negate_conclusion=True)
                    if verif.get("result") == z3.unsat:
                        unsat_candidates.append(k)
                    elif verif.get("result") == z3.sat:
                        # 2. Check if consistent (not contradicted)
                        verif_contra = verify_with_z3(unified_premises, opt_fol, negate_conclusion=False)
                        if verif_contra.get("result") != z3.unsat:
                            consistent_candidates.append(k)
                            
                # Determine final Z3 answer
                if q_type == "multiple_choice":
                    if unsat_candidates:
                        predicted_ans = sorted(unsat_candidates)
                    elif consistent_candidates:
                        predicted_ans = sorted(consistent_candidates)
                    else:
                        predicted_ans = ["Unknown"]
                else:
                    if len(unsat_candidates) == 1:
                        predicted_ans = unsat_candidates[0]
                    elif len(unsat_candidates) > 1:
                        predicted_ans = unsat_candidates[0] # Take first for simple check
                    elif len(consistent_candidates) == 1:
                        predicted_ans = consistent_candidates[0]
                    else:
                        predicted_ans = "Unknown"
                        
            else:
                # Yes/No/Uncertain flow
                conclusion_nl = pipeline._strip_question_framing(question)
                conclusion_fol_raw = translate_list_with_retry(pipeline, [conclusion_nl], glossary_str=glossary_str)[0]
                
                # Unify predicates
                all_fol = premises_fol + [conclusion_fol_raw]
                all_fol_unified = unify_fol_predicates(all_fol)
                
                unified_premises = all_fol_unified[:-1]
                unified_conclusion = all_fol_unified[-1]
                
                print(f"Unified premises FOL:\n" + "\n".join(f"  - {p}" for p in unified_premises))
                print(f"Unified conclusion FOL: {unified_conclusion}")
                
                # Check entailment
                verif = verify_with_z3(unified_premises, unified_conclusion, negate_conclusion=True)
                if verif.get("result") == z3.unsat:
                    predicted_ans = "Yes"
                else:
                    # Check if negation is entailed
                    verif_neg = verify_with_z3(unified_premises, unified_conclusion, negate_conclusion=False)
                    if verif_neg.get("result") == z3.unsat:
                        predicted_ans = "No"
                    else:
                        predicted_ans = "Uncertain"
                        
            # Compare answers
            is_match = compare_answers(gt_answer, predicted_ans)
            if is_match:
                matches += 1
                match_str = "MATCH 🟢"
            else:
                mismatches += 1
                match_str = "MISMATCH 🔴"
                
            print(f"Predicted Answer: {predicted_ans} | {match_str}")
            results.append({
                "example_id": example_id,
                "question": question,
                "gt_answer": gt_answer,
                "predicted_ans": predicted_ans,
                "is_match": is_match,
                "success": True
            })
            
        except Exception as e:
            errors += 1
            print(f"Error evaluating sample {example_id}: {e}")
            results.append({
                "example_id": example_id,
                "question": question,
                "gt_answer": gt_answer,
                "success": False,
                "error": str(e)
            })
            
    total_elapsed = time.time() - start_time
    total_evaluated = matches + mismatches
    accuracy = (matches / total_evaluated) * 100 if total_evaluated > 0 else 0.0
    
    print("\n" + "=" * 70)
    print("Z3 VERIFICATION ON VALIDATION SPLIT COMPLETED")
    print("=" * 70)
    print(f"Total evaluated: {total_evaluated}")
    print(f"Matches (Label is correct according to Z3): {matches}")
    print(f"Mismatches (Label differs from Z3 deduction): {mismatches}")
    print(f"Errors: {errors}")
    print(f"QA Accuracy: {accuracy:.2f}%")
    print(f"Total Time: {total_elapsed:.2f}s")
    print("=" * 70)
    
    # Save validation details
    out_path = root / "results" / "z3_val_evaluation_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": accuracy,
            "matches": matches,
            "mismatches": mismatches,
            "errors": errors,
            "details": results
        }, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    evaluate_val_set()
