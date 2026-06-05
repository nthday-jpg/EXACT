#!/usr/bin/env python3
import os
import re
import sys
import json
import time
from pathlib import Path

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    import z3
    from src.llm import LLMClient
    from scripts.validate_dataset_syntax import validate_sample_fol
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please make sure you are running this script inside the project virtual environment.")
    sys.exit(1)


def main():
    print("=" * 80)
    print("GRAMMAR-AWARE SPECIALIZED AUTO-REPAIR FOR FINAL 34 INVALID SAMPLES")
    print("Enforces strict quantifier nesting, uppercase connectives, qualitative math,")
    print("and alphanumeric constant renaming.")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    invalid_path = data_dir / "merged_invalid.json"
    valid_path = data_dir / "merged_valid.json"

    if not invalid_path.exists():
        print(f"Error: {invalid_path} does not exist. Run validation first.")
        sys.exit(1)

    # Load invalid samples
    with open(invalid_path, "r", encoding="utf-8") as f:
        invalid_samples = json.load(f)

    if not invalid_samples:
        print("No invalid samples found to repair!")
        sys.exit(0)

    # Initialize LLMClient with bypassed local tokenizer to force chat completions with together provider
    print("Initializing Qwen3-235B-A22B-Instruct-2507 client on Hugging Face router...")
    try:
        llm_client = LLMClient(
            model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
            extra_body={"provider": "together"},
            temperature=0.1
        )
        llm_client.tokenizer = None  # Force chat completions and correct provider routing
    except Exception as e:
        print(f"Failed to initialize LLMClient: {e}")
        sys.exit(1)

    system_prompt = """You are a Senior Logical Architect and formal logic verification expert.
Your task is to correct the 'premises-FOL' field for a batch of invalid logic samples.
Our logic parser runs a strict subset of First-Order Logic (FOL) in Python and validates them using the Z3 SMT solver.

### STRICT PARSER AND GRAMMAR RULES:
1. QUANTIFIER RULES:
   - Quantifiers MUST only quantify ONE variable at a time and must be nested.
   - CORRECT: ForAll(x, ForAll(y, P(x, y)))
   - INCORRECT: ForAll([x, y], P(x, y)) or ForAll(x, y, P(x, y)) or ForAll(x AND y, P(x, y))

2. LOGICAL CONNECTIVES:
   - Must be strictly UPPERCASE: AND, OR, NOT, ->, <->.
   - CORRECT: P(x) -> (Q(x) AND R(x))
   - INCORRECT: P(x) implies (Q(x) & R(x)) or P(x) => (Q(x) and R(x))

3. ARITHMETIC OPERATORS:
   - The parser ONLY supports addition (+) and subtraction (-).
   - The parser does NOT support division (/), multiplication (*), or exponentiation (^).
   - If a natural language premise uses division, multiplication, or mathematical equations (like Ebbinghaus R = e^(-t/S)), you MUST represent them qualitatively using functions or relations, NOT mathematical operators!
   - CORRECT: ForAll(s, ForAll(t, ForAll(S, Retention(s, t) = ForgettingValue(t, S))))
   - INCORRECT: Retention(s, t) = e^(-t/S) or Retention(s, t) = Exp(-t/S) (as SMT solver doesn't know Exp or support / operator).

4. NO SINGLE QUOTES FOR CONSTANTS:
   - Do NOT wrap constants or values (like grades a+, b+, c++ or names) in single quotes (e.g. do not write 'a+', 'c++'). Z3 treats single-quoted values as String sort, causing a sort mismatch with uninterpreted domain elements (default sort U).
   - Rename them to clean alphanumeric identifiers:
     - Rename 'c++' or c++ to cpp or cplusplus.
     - Rename 'a+' or a+ to aplus or Aplus.
     - Rename 'b+' or b+ to bplus or Bplus.
     - E.g. write Grade(aplus) instead of Grade('a+').

5. RESOLVING SORT MISMATCHES WITH NUMERICAL VALUES:
   - Avoid variable sort collisions: A variable cannot be both sort U and sort Int/Real.
   - Instead of clinical_hours(x, h) AND h >= 500, write it functionally as clinical_hours(x) >= 500 where clinical_hours is parsed as a function U -> Real.
   - Do not pass raw numbers as arguments to uninterpreted predicates (e.g., EstablishedIn(x, 2000) causes a sort mismatch). Represent them as uninterpreted constants (e.g., EstablishedIn(x, year2000)).
   - Represent relations functionally when doing numerical comparisons (e.g., instead of Credits(x, c) AND c >= 10, write Credits(x) >= 10).

6. PARENTHESES:
   - Ensure every open parenthesis '(' has a matching close parenthesis ')'.
   - Avoid spaces before argument lists: write P(x) NOT P (x).

7. CONSISTENT ARITY:
   - Ensure a predicate or function always has the exact same name casing and number of arguments across all premises in the sample (e.g. do not mix P(x) and P(x, y)).

Provide your corrected samples in a valid JSON array of objects with the exact same structure as the input, preserving all other fields (dataset_source, story_id, example_id, premises-NL, question, answer, explanation). Return JSON only, without any markdown formatting or extra text.
"""

    user_prompt_template = """Analyze and correct the following invalid logical samples under strict parser and grammar rules.
Make sure every corrected formula parses successfully with the strict parser rules!

Invalid samples:
{samples_json}

Return the strict JSON array of corrected samples only.
"""

    processed_ids = set()
    total_successful_repairs = 0
    total_failed_repairs = 0
    batch_num = 1
    batch_size = 2 # Process in small batches of 2 for highest logical focus

    while True:
        # Reload invalid samples from disk to ensure we have the most fresh state
        with open(invalid_path, "r", encoding="utf-8") as f:
            current_invalid_samples = json.load(f)

        # Select up to batch_size unprocessed invalid samples
        target_samples = [s for s in current_invalid_samples if s["example_id"] not in processed_ids][:batch_size]
        
        if not target_samples:
            print("\nAll invalid samples have been processed!")
            break

        print(f"\n" + "=" * 80)
        print(f"BATCH {batch_num} | Processing {len(target_samples)} samples (Total processed: {len(processed_ids)}/{len(invalid_samples)})")
        print("=" * 80)

        for idx, sample in enumerate(target_samples):
            print(f"  [{idx+1}] ID: {sample['example_id']} | Source: {sample['dataset_source']} | Error: {sample['validation_error']}")
            processed_ids.add(sample["example_id"])

        # Construct user prompt
        user_prompt = user_prompt_template.format(
            samples_json=json.dumps(target_samples, indent=2, ensure_ascii=False)
        )

        print("\nSending batch request to Qwen3-235B on Together...")
        try:
            response_text = llm_client.generate_text(user_prompt, system_prompt=system_prompt, max_new_tokens=4096)
        except Exception as e:
            print(f"Error during LLM text generation in Batch {batch_num}: {e}")
            continue

        # Parse response
        json_str = ""
        match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            start = response_text.find("[")
            end = response_text.rfind("]")
            if start != -1 and end != -1:
                json_str = response_text[start:end+1].strip()
            else:
                json_str = response_text.strip()

        try:
            repaired_samples = json.loads(json_str)
        except Exception as e:
            print(f"Error parsing JSON from model output in Batch {batch_num}: {e}")
            # Save raw backup for debugging
            raw_backup_path = data_dir / f"auto_repaired_raw_failed_batch_{batch_num}.json"
            with open(raw_backup_path, "w", encoding="utf-8") as f:
                f.write(response_text)
            print(f"Saved raw failed output to: {raw_backup_path.name}")
            continue

        if not isinstance(repaired_samples, list):
            print(f"Error: Repaired samples output in Batch {batch_num} is not a JSON list.")
            continue

        repaired_by_id = {s["example_id"]: s for s in repaired_samples}
        batch_successful_repairs = []

        print("\nRe-validating batch candidates with Z3...")
        for orig_sample in target_samples:
            ex_id = orig_sample["example_id"]
            if ex_id not in repaired_by_id:
                print(f"  - Sample {ex_id}: Missing from model's repaired list.")
                total_failed_repairs += 1
                continue

            repaired_sample = repaired_by_id[ex_id]
            rep_formulas = repaired_sample.get("premises-FOL", [])

            # Quick checks
            has_forbidden_chars = False
            for f in rep_formulas:
                if "/" in f or "*" in f or "[" in f or "]" in f:
                    has_forbidden_chars = True
                    break

            if has_forbidden_chars:
                print(f"  [REJECTED] Sample {ex_id}: Repair contains forbidden characters (/ or * or quantifier lists []).")
                total_failed_repairs += 1
                continue

            is_valid, error_msg = validate_sample_fol(rep_formulas)

            if is_valid:
                print(f"  [SUCCESS] Sample {ex_id}: Successfully repaired! Z3 parsed perfectly.")
                repaired_sample.pop("validation_error", None)
                batch_successful_repairs.append(repaired_sample)
                total_successful_repairs += 1
            else:
                print(f"  [FAILED] Sample {ex_id}: Repair attempt failed Z3 validation.")
                print(f"    - New Z3 error:   {error_msg}")
                total_failed_repairs += 1

        # Apply updates to disk immediately for this batch
        if batch_successful_repairs:
            print(f"\nMerging {len(batch_successful_repairs)} repaired samples...")

            # Load valid samples
            if valid_path.exists():
                with open(valid_path, "r", encoding="utf-8") as f:
                    valid_samples = json.load(f)
            else:
                valid_samples = []

            # Filter out successfully repaired samples from invalid list
            repaired_ids = {s["example_id"] for s in batch_successful_repairs}
            updated_invalid_samples = [s for s in current_invalid_samples if s["example_id"] not in repaired_ids]
            
            # Append successfully repaired samples to valid list
            valid_samples.extend(batch_successful_repairs)

            # Write updated datasets back to disk
            try:
                with open(valid_path, "w", encoding="utf-8") as f:
                    json.dump(valid_samples, f, indent=2, ensure_ascii=False)
                print(f"  -> Updated {valid_path.name} (Total valid: {len(valid_samples)})")
            except Exception as e:
                print(f"Error updating valid file: {e}")

            try:
                with open(invalid_path, "w", encoding="utf-8") as f:
                    json.dump(updated_invalid_samples, f, indent=2, ensure_ascii=False)
                print(f"  -> Updated {invalid_path.name} (Total invalid: {len(updated_invalid_samples)})")
            except Exception as e:
                print(f"Error updating invalid file: {e}")

        batch_num += 1
        # Politeness delay between batches
        time.sleep(2)

    print("\n" + "=" * 80)
    print("ALL BATCH REPAIRS COMPLETED")
    print("=" * 80)
    print(f"Total invalid samples processed: {len(processed_ids)}")
    print(f"Total successfully repaired:     {total_successful_repairs}")
    print(f"Total failed to repair:          {total_failed_repairs}")
    if len(processed_ids) > 0:
        print(f"Grand Success Rate:              {(total_successful_repairs/len(processed_ids))*100:.2f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
