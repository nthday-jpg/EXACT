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
    print("MULTI-TURN SELF-CORRECTING LOGICAL DATASET REPAIR LOOP")
    print("Runs Z3 validation feedback cycles directly with Qwen3-235B.")
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

    print(f"Loaded {len(invalid_samples)} invalid samples to repair.")

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
Your task is to analyze and correct the 'premises-FOL' field of an invalid logical dataset sample.
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

Provide your corrected sample as a single valid JSON object matching our unified schema. Return JSON only, without any markdown formatting or extra text.
"""

    total_successful = 0
    total_failed = 0
    start_time = time.time()

    # We iterate over a copy of invalid samples to safely edit datasets
    for idx, sample in enumerate(invalid_samples, start=1):
        ex_id = sample["example_id"]
        source = sample["dataset_source"]
        orig_error = sample["validation_error"]

        print(f"\n" + "=" * 80)
        print(f"SAMPLE {idx}/{len(invalid_samples)} | ID: {ex_id} | Source: {source}")
        print(f"Current Z3 Error: {orig_error}")
        print("=" * 80)

        # Setup multi-turn chat messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please correct this invalid sample under our strict parser and grammar rules. Ensure all premises-FOL match our constraints exactly:\n\n{json.dumps(sample, indent=2, ensure_ascii=False)}\n\nReturn the corrected JSON object only."}
        ]

        success = False
        repaired_sample = None

        for turn in range(1, 4):
            print(f"  [TURN {turn}] Generating correction...")
            try:
                # Call generative API directly
                response_text = llm_client.generate_text(
                    messages[-1]["content"] if turn > 1 else messages[1]["content"],
                    system_prompt=system_prompt,
                    max_new_tokens=2048
                )
            except Exception as e:
                print(f"    - LLM Call failed: {e}")
                break

            # Parse response JSON
            json_str = ""
            match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
            else:
                start = response_text.find("{")
                end = response_text.rfind("}")
                if start != -1 and end != -1:
                    json_str = response_text[start:end+1].strip()
                else:
                    json_str = response_text.strip()

            try:
                repaired_sample = json.loads(json_str)
            except Exception as e:
                print(f"    - Failed to parse JSON: {e}")
                # Save raw backup for debugging
                continue

            if not isinstance(repaired_sample, dict):
                print("    - Error: Response is not a JSON object dictionary.")
                continue

            rep_formulas = repaired_sample.get("premises-FOL", [])

            # Constraint checks
            forbidden_issues = []
            for f in rep_formulas:
                if "/" in f:
                    forbidden_issues.append(f"Contains division '/': '{f}'")
                if "*" in f:
                    forbidden_issues.append(f"Contains multiplication '*': '{f}'")
                if "[" in f or "]" in f:
                    forbidden_issues.append(f"Contains quantifier list [] brackets: '{f}'")

            if forbidden_issues:
                error_msg = "Forbidden syntax check failed:\n" + "\n".join(forbidden_issues)
                print(f"    - Guidance violation: {error_msg}")
            else:
                # Z3 validation
                is_valid, error_msg = validate_sample_fol(rep_formulas)

            if not forbidden_issues and is_valid:
                print(f"    [SUCCESS] Sample {ex_id}: Successfully repaired and verified by Z3 parser!")
                repaired_sample.pop("validation_error", None)
                success = True
                total_successful += 1
                break
            else:
                # Prepare feedback for next turn
                print(f"    [FAILED] Repair validation failed.")
                print(f"      - Error: {error_msg}")
                
                feedback_prompt = f"""Your proposed FOL formulas failed validation. Please fix the error.

[Z3 parser error / constraint violations]:
{error_msg}

[Strict rules reminder]:
1. Do not use [x, y] inside quantifiers. Use nested ForAll(x, ForAll(y, ...)).
2. Do not use '/' or '*' operators. Represent divisions/multiplications qualitatively using function applications or uninterpreted predicates (e.g. Forgetting(t, S) or exp_val(t, S)).
3. Keep logical connectives strictly UPPERCASE: AND, OR, NOT, ->, <->.
4. Do not use single quotes around constant names. E.g. Grade(aplus) instead of Grade('a+').

Please correct the formulas and return the complete, cleaned JSON object only."""
                
                # Append history
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": feedback_prompt})

        # Apply disk update immediately if repaired
        if success and repaired_sample:
            # Reload datasets to prevent race conditions
            with open(valid_path, "r", encoding="utf-8") as f:
                valid_samples = json.load(f)
            with open(invalid_path, "r", encoding="utf-8") as f:
                current_invalid_samples = json.load(f)

            # Update valid and invalid
            valid_samples.append(repaired_sample)
            updated_invalid = [s for s in current_invalid_samples if s["example_id"] != ex_id]

            try:
                with open(valid_path, "w", encoding="utf-8") as f:
                    json.dump(valid_samples, f, indent=2, ensure_ascii=False)
                with open(invalid_path, "w", encoding="utf-8") as f:
                    json.dump(updated_invalid, f, indent=2, ensure_ascii=False)
                print(f"  -> Merged {ex_id} to valid file (Total valid: {len(valid_samples)}, Total invalid: {len(updated_invalid)})")
            except Exception as e:
                print(f"  -> Error updating files: {e}")
        else:
            total_failed += 1
            print(f"  -> Failed to repair {ex_id} after 3 attempts.")

        # Politeness delay
        time.sleep(2)

    print("\n" + "=" * 80)
    print("MULTI-TURN SELF-CORRECTING LOGICAL DATASET REPAIR COMPLETED")
    print("=" * 80)
    print(f"Total processed:         {len(invalid_samples)}")
    print(f"Total successfully fixed: {total_successful}")
    print(f"Total remaining invalid:  {total_failed}")
    print(f"Execution time:          {time.time() - start_time:.2f} seconds")
    print("=" * 80)


if __name__ == "__main__":
    main()
