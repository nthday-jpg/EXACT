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
    print("LLM-ASSISTED DATASET BATCH REPAIR WITH QWEN3-235B")
    print("Processes all invalid samples in batches of 3 until completion.")
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

    processed_ids = set()
    total_successful_repairs = 0
    total_failed_repairs = 0
    batch_num = 1

    prompt_template = """You are a precise logical reasoning assistant and expert in First-Order Logic (FOL) and Z3 syntax.
Your task is to analyze and correct 3 invalid logical samples from our dataset.
Each sample has been marked as invalid by our Z3 validation tool because of syntax errors, predicate inconsistencies, glossary mismatches, or sort/arity mismatches in the 'premises-FOL' field.

For each sample, you must analyze and check:
1. NL ↔ FOL semantic fidelity: Does the FOL logic accurately reflect the meaning of the natural language premises?
2. Predicate consistency: Are predicate names used consistently across all premises? (e.g. not 'Women' and 'women', or 'Drinks' vs 'Drink')
3. Glossary consistency: Do we have uniform vocabulary/terms representing the same entities?
4. Syntax consistency: Are Z3 operators, connectives, variables, and quantifiers syntactically valid and properly structured?
5. Answer verification: Does the target question/conclusion answer match the logical result?

### CRITICAL Z3 syntax and sort matching requirements for 'premises-FOL':
- Use standard uppercase Z3 logical connectives: `AND`, `OR`, `NOT`, `->`, `<->`.
- Quantifiers MUST be formatted exactly as: `ForAll(x, ...)` or `Exists(x, ...)`.
- **NO SINGLE QUOTES FOR CONSTANTS OR GRADES**: Do not wrap constants like `a+`, `b+`, `c++`, or standard names in single quotes (e.g. do NOT write `'a+'` or `'c++'`). Single quotes are parsed as `String` type, causing a Z3 `Sort mismatch` when mixed with standard uninterpreted constants (which have the default domain sort `U`).
- **RENAME SPECIAL CHARACTER CONSTANTS TO ALPHANUMERIC IDENTIFIERS**:
  - Rename `c++` to `cpp` (e.g. write `WrittenIn(x, cpp)` or `cplusplus`).
  - Rename `a+` to `aplus` or `Aplus` (e.g. write `Grade(aplus)`).
  - Rename `b+` to `bplus` or `Bplus` (e.g. write `Grade(bplus)`).
  - In general, use standard valid Python-style variable/constant names (letters, digits, underscores).
- **RESOLVING ADVANCED SORT MISMATCHES WITH NUMERICAL VALUES**:
  If a natural language premise involves numerical values, years, grades, or comparisons (e.g., 'clinical hours >= 500', 'GPA of 3.0', 'established in 2000'):
  1. **Do NOT pass raw numbers into standard relational predicates** like `EstablishedIn(x, 2000)`. Z3 treats `2000` as `Int` sort, causing a sort mismatch with uninterpreted constants of sort `U`. Instead, represent years or non-compared numbers as standard uninterpreted identifiers (e.g., write `EstablishedIn(x, year2000)` instead of `EstablishedIn(x, 2000)`).
  2. **Avoid variable sort collisions**: A variable `h` cannot be both sort `U` and sort `Int`/`Real`. Instead of writing `clinical_hours(x, h) AND h >= 500`, write it functionally as `clinical_hours(x) >= 500` where `clinical_hours` is parsed as a function `U -> Real`. Similarly, instead of `Semester(Nam) = 3 AND GPA(Nam) = 3.0`, write `Semester(Nam) = 3 AND GPA(Nam) = 3.0` which is correct, but ensure the function is consistently treated as returning a number.
  3. Ensure that if a function returns a number, it is always compared with numbers (e.g., `GPA(x) >= 3.0`), and if a predicate takes constants, it never receives raw numbers.
- Every open parenthesis must have a matching closing parenthesis.
- All occurrences of a predicate name must have the EXACT same case and number of arguments (e.g. do not mix `P(x)` and `P(x, y)` in the same sample).

### OUTPUT FORMAT:
Provide the corrected samples as a single, valid JSON array containing exactly the corrected samples matching the unified schema. Do not add any conversational text or explanation outside the JSON block.
Unified Schema format:
```json
[
  {{
    "dataset_source": "...",
    "story_id": "...",
    "example_id": "...",
    "premises-NL": [ ... ],
    "premises-FOL": [ ... ],
    "question": "...",
    "answer": "...",
    "explanation": "..."
  }},
  ...
]
```

Here are the invalid samples to check and repair:
"""

    while True:
        # Reload invalid samples from disk to ensure we have the most fresh state
        with open(invalid_path, "r", encoding="utf-8") as f:
            current_invalid_samples = json.load(f)

        # Select up to 3 unprocessed invalid samples
        target_samples = [s for s in current_invalid_samples if s["example_id"] not in processed_ids][:3]
        
        if not target_samples:
            print("\nAll invalid samples have been processed!")
            break

        print(f"\n" + "=" * 80)
        print(f"BATCH {batch_num} | Processing {len(target_samples)} samples (Total processed: {len(processed_ids)}/{len(invalid_samples)})")
        print("=" * 80)

        for idx, sample in enumerate(target_samples):
            print(f"  [{idx+1}] ID: {sample['example_id']} | Source: {sample['dataset_source']} | Error: {sample['validation_error']}")
            processed_ids.add(sample["example_id"])

        # Construct prompt for this batch
        prompt = prompt_template + json.dumps(target_samples, indent=2, ensure_ascii=False)

        print("\nSending batch request to Qwen3-235B on Together...")
        try:
            response_text = llm_client.generate_text(prompt, max_new_tokens=4096)
        except Exception as e:
            print(f"Error during LLM text generation in Batch {batch_num}: {e}")
            print("Skipping this batch...")
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
            raw_backup_path = data_dir / f"repaired_raw_failed_batch_{batch_num}.json"
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
        # Polite delay between batches
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
