import json
import os
import sys
import re
import io
import argparse
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Enable Z3 proof generation globally before importing other Z3 modules
import z3
z3.set_param('proof', True)
from z3 import Solver, unsat, sat, Not, DeclareSort

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from llm.llm_client import LLMClient
from src.logic.reasoning.verifier import parse_formulas, FolParser, Z3Symbols
from src.utils.normalization import normalize_logic_fol_entry

# Preset samples for testing contradiction
SAMPLES = {
    0: {
        "name": "Python Project Optimization",
        "conclusion": "If all Python projects are well-structured, then all Python projects are optimized."
    },
    1: {
        "name": "Sophia's Scholarship",
        "conclusion": "Sophia qualifies for the university scholarship."
    },
    3: {
        "name": "John's Fellowship",
        "conclusion": "John qualifies for the graduate fellowship program."
    },
    13: {
        "name": "Sarah's Course Eligibility",
        "conclusion": "Sarah is eligible for advanced classes."
    }
}

def extract_fol_formulas(text: str) -> list[str]:
    """Extract FOL formulas directly from conversational LLM output without post-processing cleanup."""
    # Robustly strip <think>...</think> reasoning blocks if present
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    
    # Try parsing as JSON list first, as the model was fine-tuned to produce valid JSON lists
    try:
        cleaned_text = text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\n", "", cleaned_text)
            cleaned_text = re.sub(r"\n```$", "", cleaned_text)
        
        parsed = json.loads(cleaned_text.strip())
        if isinstance(parsed, list):
            return [item.strip() for item in parsed if isinstance(item, str)]
    except Exception:
        pass

    # Fallback to line-by-line parsing if JSON parsing fails
    lines = text.strip().split("\n")
    fol_formulas = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Stop extracting if we hit common explanation separators or headers
        if any(marker in line for marker in ["---", "Key Predicates", "Explanation:", "Predicate Key", "Key:", "Predicates:", "Notes:", "Key predicates:"]):
            break
            
        # Ignore description lines which typically contain a colon ":"
        if ":" in line:
            continue
            
        # Strip list prefixes like "1. ", "10. ", "1) "
        line = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
        
        # Remove quotes and trailing commas that might come from poorly formatted pseudo-JSON
        line = line.strip('"').strip("'").rstrip(",")
        
        if line:
            fol_formulas.append(line)
    return fol_formulas

def parse_options(question_text: str) -> dict[str, str]:
    """Parse options A, B, C, D from the question text."""
    options = {}
    pattern = r'(?:\s+|^)([A-D])\.\s+(.*?)(?=\s+[A-D]\.\s+|$)'
    matches = re.findall(pattern, question_text, re.DOTALL)
    for opt_char, opt_text in matches:
        options[opt_char] = opt_text.strip()
    return options

def standardize_formula(f_str: str) -> str:
    """Standardize FOL formula operators and fix common casing errors."""
    f_clean = f_str.replace("¬", " NOT ").replace("∧", " AND ").replace("∨", " OR ").replace("→", " -> ").replace("↔", " <-> ")
    # Replace case-insensitive and/or/not with word boundaries
    f_clean = re.sub(r"\b[Aa]nd\b", " AND ", f_clean)
    f_clean = re.sub(r"\b[Oo]r\b", " OR ", f_clean)
    f_clean = re.sub(r"\b[Nn]ot\b", " NOT ", f_clean)
    # Balance parentheses
    open_count = f_clean.count("(")
    close_count = f_clean.count(")")
    if close_count < open_count:
        f_clean = f_clean + ")" * (open_count - close_count)
    return f_clean

def evaluate_sample(sample_idx: int, sample: dict, client: LLMClient) -> dict:
    """Evaluate a single sample: translate premises and options, check entailment with Z3."""
    log_lines = []
    
    premises_nl = sample["premises-NL"]
    questions = sample.get("questions", [])
    if not questions:
        return {
            "success": False,
            "reason": "lacks questions",
            "log": f"\nSkipping sample {sample_idx} because it lacks questions."
        }
        
    q0 = questions[0]
    options = parse_options(q0)
    
    if not options or len(options) < 4:
        return {
            "success": False,
            "reason": "option parsing failed",
            "log": f"\nSkipping sample {sample_idx} because option parsing failed or fewer than 4 options were found."
        }
        
    correct_ans = sample.get("answers", [None])[0]
    
    log_lines.append("\n" + "=" * 70)
    log_lines.append(f"Sample Index {sample_idx} | Correct Answer: {correct_ans}")
    log_lines.append("=" * 70)
    log_lines.append("--- Premises ---")
    for idx, premise in enumerate(premises_nl, 1):
        log_lines.append(f"{idx}. {premise}")
    log_lines.append("\n--- Options ---")
    for opt_char in ["A", "B", "C", "D"]:
        log_lines.append(f"{opt_char}. {options[opt_char]}")
    log_lines.append("-" * 70)
    
    # Combine premises and the 4 options
    sorted_options = [options[k] for k in ["A", "B", "C", "D"]]
    combined_nl_list = premises_nl + sorted_options
    
    nl_content = ""
    for i, nl in enumerate(combined_nl_list, start=1):
        nl_content += f"{i}. {nl}\n"
        
    user_prompt = (
        "Convert the following premises into canonical first-order logic.\n\n"
        "Premises:\n"
        f"{nl_content.strip()}\n\n"
        "Return a JSON list of strings containing the formulas."
    )
    
    log_lines.append("\nTranslating Premises + 4 Options in a single LLM call (ensures predicate alignment)...")
    response_content = ""
    max_retries = 8
    import time
    import random
    for attempt in range(max_retries):
        try:
            response = client.generate(user_prompt.strip(), max_tokens=None)
            response_content = response["content"]
            break
        except Exception as e:
            err_msg = str(e)
            if "concurrency_limit_exceeded" in err_msg or "429" in err_msg:
                wait_time = random.uniform(1.5, 3.5) * (attempt + 1)
                log_lines.append(f"[Attempt {attempt + 1}/{max_retries}] Concurrency/Rate limit hit. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                log_lines.append(f"Error calling LLM: {e}")
                return {
                    "success": False,
                    "reason": f"LLM error: {str(e)}",
                    "log": "\n".join(log_lines)
                }
    else:
        log_lines.append("Failed to translate after max retries due to LLM concurrency/rate limits.")
        return {
            "success": False,
            "reason": "Max retries exceeded (Rate Limit)",
            "log": "\n".join(log_lines)
        }
        
    all_extracted_fol = extract_fol_formulas(response_content)
    expected_count = len(combined_nl_list)
    
    if len(all_extracted_fol) < expected_count:
        log_lines.append(f"WARNING: Extracted {len(all_extracted_fol)} formulas but expected {expected_count}.")
        premises_fol = all_extracted_fol[:len(premises_nl)]
        options_fol = {}
        for i, opt_char in enumerate(["A", "B", "C", "D"]):
            offset = len(premises_nl) + i
            options_fol[opt_char] = all_extracted_fol[offset] if offset < len(all_extracted_fol) else ""
    else:
        premises_fol = all_extracted_fol[:len(premises_nl)]
        options_fol = {
            "A": all_extracted_fol[len(premises_nl)],
            "B": all_extracted_fol[len(premises_nl) + 1],
            "C": all_extracted_fol[len(premises_nl) + 2],
            "D": all_extracted_fol[len(premises_nl) + 3]
        }
        
    log_lines.append("\n--- Extracted FOL ---")
    for i, fol in enumerate(premises_fol, 1):
        log_lines.append(f"Premise {i}: {fol}")
    for opt_char in ["A", "B", "C", "D"]:
        log_lines.append(f"{opt_char}: {options_fol.get(opt_char, '')}")
    log_lines.append("-" * 70)
    
    # Parse premises using Z3 symbols
    standardized_premises = [standardize_formula(f) for f in premises_fol]
    try:
        symbols, premise_exprs = parse_formulas(standardized_premises)
    except Exception as e:
        log_lines.append(f"Failed to parse premises FOL: {e}")
        return {
            "success": False,
            "reason": f"Premise parse error: {str(e)}",
            "log": "\n".join(log_lines)
        }
            
    parser = FolParser(symbols)
    satisfied_options = []
    option_results = {}
    
    for opt_char in ["A", "B", "C", "D"]:
        opt_fol = options_fol.get(opt_char, "")
        if not opt_fol:
            option_results[opt_char] = "PARSE_ERROR"
            continue
            
        try:
            opt_clean = standardize_formula(opt_fol)
            negated_opt_clean = f"NOT ({opt_clean})"
            negated_expr = parser.parse(negated_opt_clean)
            
            # Check with Z3
            solver = Solver()
            solver.add(*premise_exprs)
            solver.add(negated_expr)
            
            res = solver.check()
            option_results[opt_char] = str(res)
            if res == unsat:
                satisfied_options.append(opt_char)
        except Exception as e:
            option_results[opt_char] = f"ERROR: {str(e)}"
            
    log_lines.append("\n--- Z3 Options Satisfaction Check ---")
    for opt_char in ["A", "B", "C", "D"]:
        res_str = option_results[opt_char]
        status = ""
        if res_str == "unsat":
            status = "🟢 SATISFIED (ENTAILED)"
        elif res_str == "sat":
            status = "🔴 NOT SATISFIED (CONSISTENT/NOT ENTAILED)"
        else:
            status = f"🟡 {res_str}"
        log_lines.append(f"Option {opt_char}: {status}")
        
    log_lines.append(f"\nGround Truth Answer: {correct_ans}")
    log_lines.append(f"Z3 Satisfied Options: {satisfied_options}")
    
    is_match = correct_ans in satisfied_options
    if is_match:
        log_lines.append("➡️ MATCH: Z3 successfully proved the correct answer!")
    else:
        log_lines.append("➡️ MISMATCH: Z3 did not prove the correct answer.")
        
    return {
        "success": True,
        "is_match": is_match,
        "correct_ans": correct_ans,
        "satisfied_options": satisfied_options,
        "log": "\n".join(log_lines)
    }

def main():
    load_dotenv()
    
    # Parse command line args
    parser = argparse.ArgumentParser(description="Run complete contradiction tests on logic_based dataset options A, B, C, D")
    parser.add_argument("--index", "-i", type=int, default=None, help="Index of the single sample to test")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Number of samples to evaluate")
    parser.add_argument("--all", "-a", action="store_true", help="Evaluate the entire dataset")
    parser.add_argument("--jobs", "-j", type=int, default=1, help="Number of concurrent worker threads")
    args = parser.parse_args()
    
    # Get model and API key configuration
    logic_model_name = os.getenv("LOGIC_COMPILER_MODEL", "Qwen/Qwen3-8B:featherless-ai")
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        print("ERROR: HF_API_KEY is not set in the environment.")
        sys.exit(1)
        
    print("=" * 70)
    print("TESTING FINE-TUNED MODEL & FORMAL PROOF CONTRADICTION (Z3) FOR OPTIONS A-D")
    print(f"Model name: {logic_model_name}")
    print("=" * 70)
    
    # 1. Load unprocessed dataset
    data_path = root_dir / "data" / "logic_based.json"
    if not data_path.exists():
        print(f"ERROR: Dataset not found at {data_path}")
        sys.exit(1)
        
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    # Determine indices to run
    if args.index is not None:
        indices = [args.index]
    elif args.all:
        indices = list(range(len(dataset)))
    elif args.limit is not None:
        indices = list(range(min(args.limit, len(dataset))))
    else:
        # Default behavior: run Sophia's Scholarship (index 1) and show help info
        indices = [1]
        print("Tip: You can use --limit <N>, --index <IDX>, or --all to evaluate more samples.")
        
    print(f"Evaluating {len(indices)} sample(s): {indices}")
    
    # Initialize LLM Client
    system_prompt = (
        "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
        "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n\n"
        "ALLOWED OPERATORS:\n"
        "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
        "QUANTIFIER RULES:\n"
        "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
        "Return JSON only."
    )
    client = LLMClient(
        model_name=logic_model_name,
        api_key=api_key,
        system_prompt=system_prompt,
        temperature=0.1
    )
    
    correct_count = 0
    attempted_count = 0
    
    if args.jobs > 1:
        print(f"Running in parallel with {args.jobs} workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            future_to_idx = {
                executor.submit(evaluate_sample, idx, dataset[idx], client): idx
                for idx in indices if idx < len(dataset)
            }
            
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    print(result["log"])
                    if result.get("success"):
                        attempted_count += 1
                        if result["is_match"]:
                            correct_count += 1
                except Exception as exc:
                    print(f"\nSample {idx} generated an exception: {exc}")
    else:
        print("Running sequentially...")
        for sample_idx in indices:
            if sample_idx >= len(dataset):
                print(f"\nIndex {sample_idx} is out of bounds (dataset size: {len(dataset)}). Skipping.")
                continue
            try:
                result = evaluate_sample(sample_idx, dataset[sample_idx], client)
                print(result["log"])
                if result.get("success"):
                    attempted_count += 1
                    if result["is_match"]:
                        correct_count += 1
            except Exception as exc:
                print(f"\nSample {sample_idx} generated an exception: {exc}")
                
    if attempted_count > 0:
        accuracy = (correct_count / attempted_count) * 100
        print("\n" + "=" * 70)
        print("EVALUATION SUMMARY")
        print("=" * 70)
        print(f"Total Samples Attempted: {attempted_count}")
        print(f"Z3 Satisfied Correct Answer: {correct_count}")
        print(f"Entailment Accuracy: {accuracy:.2f}%")
        print("=" * 70)
if __name__ == "__main__":
    main()
