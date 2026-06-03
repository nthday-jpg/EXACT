#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import shutil
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    from src.llm import LLMClient
    from scripts.validate_dataset_syntax import validate_sample_fol
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


SYSTEM_PROMPT = """You are a Senior Logical Architect and formal logic verification expert.
Your task is to correct a logic dataset story sample so that the list of natural language premises ('premises-NL') and the list of First-Order Logic formulas ('premises-FOL') have the EXACT SAME length (1-to-1 alignment).
Currently, the number of elements in 'premises-NL' does not match 'premises-FOL'.
For every index i, 'premises-FOL[i]' must be the precise logical translation of 'premises-NL[i]'.

### STRICT PARSER AND GRAMMAR RULES:
1. QUANTIFIER RULES:
   - Quantifiers MUST only quantify ONE variable at a time and must be nested.
   - CORRECT: ForAll(x, ForAll(y, P(x, y)))
   - INCORRECT: ForAll([x, y], P(x, y)) or ForAll(x, y, P(x, y)) or ForAll(x AND y, P(x, y)) - Never use list brackets [] in ForAll or Exists!

2. LOGICAL CONNECTIVES:
   - Must be strictly UPPERCASE: AND, OR, NOT, ->, <->.
   - CORRECT: P(x) -> (Q(x) AND R(x))

3. ARITHMETIC OPERATORS:
   - The parser ONLY supports addition (+) and subtraction (-).
   - The parser does NOT support division (/), multiplication (*), or exponentiation (^).
   - If a natural language premise uses division, multiplication, or mathematical equations, you MUST represent them qualitatively using functions or relations, NOT mathematical operators!
   - CORRECT: ForAll(s, ForAll(t, ForAll(S, Retention(s, t) = ForgettingValue(t, S))))
   - INCORRECT: Retention(s, t) = e^(-t/S) or Retention(s, t) = Exp(-t/S) (as SMT solver doesn't know Exp or support / operator).

4. NO SINGLE QUOTES FOR CONSTANTS:
   - Do NOT wrap constants or values (like grades a+, b+, c++ or names) in single quotes (e.g. do not write 'a+', 'c++'). Z3 treats single-quoted values as String sort, causing a sort mismatch with uninterpreted domain elements (default sort U).
   - Rename them to clean alphanumeric identifiers:
     - E.g. write Grade(aplus) instead of Grade('a+').

5. RESOLVING SORT MISMATCHES WITH NUMERICAL VALUES:
   - Avoid variable sort collisions: A variable cannot be both sort U and sort Int/Real.
   - Instead of clinical_hours(x, h) AND h >= 500, write it functionally as clinical_hours(x) >= 500 where clinical_hours is parsed as a function U -> Real.
   - Do not pass raw numbers as arguments to uninterpreted predicates (e.g., EstablishedIn(x, 2000) causes a sort mismatch). Represent them as uninterpreted constants (e.g., EstablishedIn(x, year2000)).

6. PARENTHESES:
   - Ensure every open parenthesis '(' has a matching close parenthesis ')'.
   - Avoid spaces before argument lists: write P(x) NOT P (x).

7. CONSISTENT ARITY:
   - Ensure a predicate or function always has the exact same name casing and number of arguments across all premises in the sample (e.g. do not mix P(x) and P(x, y)).

8. ZERO-ARITY PREDICATES:
   - Write empty parentheses '()' for zero-arity predicates (like depleted_fund()).

### OUTPUT FORMAT:
Provide the corrected story as a single, valid JSON object containing the field 'premises-FOL' which is a list of corrected FOL formulas matching the length of 'premises-NL'. Return JSON only, without any markdown formatting or extra text.
"""

USER_PROMPT_TEMPLATE = """Please repair this sample so that 'premises-NL' and 'premises-FOL' have the exact same number of elements (1-to-1 alignment).
Each FOL formula must logically translate the corresponding NL premise at the same index.

Sample to repair:
{sample_json}

Return the repaired JSON object containing the field 'premises-FOL'.
"""

FEEDBACK_TEMPLATE = """Your previous repair failed validation. Please fix the following issue(s):

{error_msg}

Please align 'premises-NL' ({len_nl} items) and 'premises-FOL' ({len_fol} items) 1:1, correct Z3 errors, and return the corrected JSON object containing the field 'premises-FOL' only."""


def repair_sample(llm_client, sample, idx_label, max_retries=3):
    sample_json = json.dumps(sample, indent=2, ensure_ascii=False)
    user_prompt = USER_PROMPT_TEMPLATE.format(sample_json=sample_json)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    for turn in range(1, max_retries + 1):
        print(f"    [Turn {turn}] Sending request to LLM...")
        try:
            current_user_content = messages[-1]["content"] if turn > 1 else user_prompt
            response_text = llm_client.generate_text(current_user_content, system_prompt=SYSTEM_PROMPT, max_new_tokens=4096)
        except Exception as e:
            print(f"      - LLM call failed: {e}")
            time.sleep(2)
            continue

        # Extract JSON block
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
            repaired_data = json.loads(json_str)
        except Exception as e:
            print(f"      - Turn {turn}: Failed to parse JSON: {e}")
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": "Failed to parse your response as JSON. Please return valid JSON only."})
            continue

        fol = repaired_data.get("premises-FOL", [])
        nl = sample["premises-NL"]
        
        # Check lengths
        if len(nl) != len(fol):
            error_msg = f"Length mismatch: premises-NL has {len(nl)} items, but premises-FOL has {len(fol)} items. They must match 1:1."
            print(f"      - Turn {turn}: {error_msg}")
            messages.append({"role": "assistant", "content": json.dumps(repaired_data, ensure_ascii=False)})
            messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, len_nl=len(nl), len_fol=len(fol))})
            continue

        # Z3 syntax checker (exclude basic forbidden chars)
        forbidden = []
        for f in fol:
            if "/" in f: forbidden.append(f"Contains division '/': {f}")
            if "*" in f: forbidden.append(f"Contains multiplication '*': {f}")
            if "[" in f or "]" in f: forbidden.append(f"Contains brackets []: {f}")

        if forbidden:
            error_msg = "Forbidden syntax check failed:\n" + "\n".join(forbidden)
            print(f"      - Turn {turn}: {error_msg}")
            messages.append({"role": "assistant", "content": json.dumps(repaired_data, ensure_ascii=False)})
            messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, len_nl=len(nl), len_fol=len(fol))})
            continue

        # Run Z3 validator
        is_valid, z3_error = validate_sample_fol(fol)
        if not is_valid:
            error_msg = f"Z3 parser error / constraint violation: {z3_error}"
            print(f"      - Turn {turn}: {error_msg}")
            messages.append({"role": "assistant", "content": json.dumps(repaired_data, ensure_ascii=False)})
            messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, len_nl=len(nl), len_fol=len(fol))})
            continue

        # Success!
        print(f"      - [SUCCESS] Repaired successfully at turn {turn}!")
        return True, fol

    return False, None


def main():
    print("=" * 80)
    print("REPAIRING MISMATCHED PREMISE COUNTS IN LOGIC_MERGED_VALID.JSON")
    print("=" * 80)

    path = root_dir / "data" / "processed" / "logic_merged_valid.json"
    if not path.exists():
        print(f"Error: {path} not found.")
        sys.exit(1)

    # 1. Unique sample extraction using exact user logic
    samples = []
    seen_premises = set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        nl_list = item.get("premises-NL", [])
        fol_list = item.get("premises-FOL", [])
        if not nl_list or not fol_list:
            continue
        nl_serialized = "\n".join(nl_list)
        if nl_serialized in seen_premises:
            continue
        seen_premises.add(nl_serialized)
        samples.append({"premises-NL": nl_list, "premises-FOL": fol_list})
    print(f"Loaded {len(samples)} unique translation samples from {os.path.basename(path)}")

    # 2. Check unique samples with len(nl_list) != len(fol_list)
    mismatched_samples = []
    for idx, item in enumerate(samples):
        nl = item["premises-NL"]
        fol = item["premises-FOL"]
        if len(nl) != len(fol):
            mismatched_samples.append((idx, item))

    print(f"Found {len(mismatched_samples)} unique mismatched samples.")
    if not mismatched_samples:
        print("No mismatched samples to repair. Exiting.")
        sys.exit(0)

    # Initialize LLM Client
    print("\nInitializing Qwen3-235B client on Hugging Face router...")
    try:
        llm_client = LLMClient(
            model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
            extra_body={"provider": "together"},
            temperature=0.1
        )
        llm_client.tokenizer = None
    except Exception as e:
        print(f"Failed to initialize LLMClient: {e}")
        sys.exit(1)

    repaired_map = {}
    success_count = 0

    for pos, (orig_idx, sample) in enumerate(mismatched_samples, 1):
        nl = sample["premises-NL"]
        fol = sample["premises-FOL"]
        print(f"\n[{pos}/{len(mismatched_samples)}] Repairing sample index {orig_idx}...")
        print(f"    NL premises count: {len(nl)} | FOL premises count: {len(fol)}")
        
        success, repaired_fol = repair_sample(llm_client, sample, orig_idx)
        if success:
            nl_serialized = "\n".join(nl)
            repaired_map[nl_serialized] = repaired_fol
            success_count += 1
        else:
            print(f"    [FAILED] Could not repair sample index {orig_idx}.")
        
        time.sleep(2)

    print(f"\nSuccessfully repaired {success_count}/{len(mismatched_samples)} samples.")

    if success_count > 0:
        # Create a backup
        backup_path = path.with_suffix(".json.bak")
        print(f"\nCreating backup of original file at {backup_path.name}...")
        shutil.copy2(path, backup_path)

        # Update all matching occurrences in original file
        print("Applying repairs to all matching occurrences in the dataset...")
        update_count = 0
        for item in data:
            nl_list = item.get("premises-NL", [])
            nl_serialized = "\n".join(nl_list)
            if nl_serialized in repaired_map:
                item["premises-FOL"] = repaired_map[nl_serialized]
                # Also remove validation_error if it exists
                item.pop("validation_error", None)
                update_count += 1

        print(f"Updated {update_count} samples in {path.name}.")

        # Save the repaired file
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Repaired dataset saved successfully.")

    print("\n" + "=" * 80)
    print("REPAIR PROCESS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
