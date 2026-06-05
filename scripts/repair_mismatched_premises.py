#!/usr/bin/env python3
import os
import re
import sys
import json
import time
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
Provide the corrected story as a single, valid JSON object with the exact same structure as the input, preserving all other fields (idx, questions, answers, explanation). Return JSON only, without any markdown formatting or extra text.
"""

USER_PROMPT_TEMPLATE = """Please repair this sample so that 'premises-NL' and 'premises-FOL' have the exact same number of elements (1-to-1 alignment).
Each FOL formula must logically translate the corresponding NL premise at the same index.

Sample to repair:
{sample_json}

Return the repaired JSON object matching the exact structure of the input.
"""

FEEDBACK_TEMPLATE = """Your previous repair failed validation. Please fix the following issue(s):

{error_msg}

Please align 'premises-NL' ({len_nl} items) and 'premises-FOL' ({len_fol} items) 1:1, correct Z3 errors, and return the complete corrected JSON object only."""


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
            repaired_sample = json.loads(json_str)
        except Exception as e:
            print(f"      - Turn {turn}: Failed to parse JSON: {e}")
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": "Failed to parse your response as JSON. Please return valid JSON only."})
            continue

        nl = repaired_sample.get("premises-NL", [])
        fol = repaired_sample.get("premises-FOL", [])
        
        # Check lengths
        if len(nl) != len(fol):
            error_msg = f"Length mismatch: premises-NL has {len(nl)} items, but premises-FOL has {len(fol)} items. They must match 1:1."
            print(f"      - Turn {turn}: {error_msg}")
            messages.append({"role": "assistant", "content": json.dumps(repaired_sample, ensure_ascii=False)})
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
            messages.append({"role": "assistant", "content": json.dumps(repaired_sample, ensure_ascii=False)})
            messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, len_nl=len(nl), len_fol=len(fol))})
            continue

        # Run Z3 validator
        is_valid, z3_error = validate_sample_fol(fol)
        if not is_valid:
            error_msg = f"Z3 parser error / constraint violation: {z3_error}"
            print(f"      - Turn {turn}: {error_msg}")
            messages.append({"role": "assistant", "content": json.dumps(repaired_sample, ensure_ascii=False)})
            messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, len_nl=len(nl), len_fol=len(fol))})
            continue

        # Success!
        print(f"      - [SUCCESS] Repaired successfully at turn {turn}!")
        return True, repaired_sample

    return False, sample


def main():
    print("=" * 80)
    print("REPAIRING MISMATCHED PREMISE COUNTS IN LOGIC_BASED.JSON")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    input_file = data_dir / "logic_based.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} stories from logic_based.json.")

    mismatched_indices = []
    for idx, sample in enumerate(dataset):
        nl = sample.get("premises-NL", [])
        fol = sample.get("premises-FOL", [])
        if len(nl) != len(fol):
            mismatched_indices.append(idx)

    print(f"Found {len(mismatched_indices)} mismatched stories: {mismatched_indices}")

    if not mismatched_indices:
        print("No mismatched stories to repair!")
        sys.exit(0)

    print("\nInitializing Qwen3-235B client on Hugging Face router...")
    try:
        llm_client = LLMClient(
            model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
            temperature=0.1
        )
        llm_client.tokenizer = None
    except Exception as e:
        print(f"Failed to initialize LLMClient: {e}")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    for pos, idx in enumerate(mismatched_indices, 1):
        sample = dataset[idx]
        story_id = sample.get("story_id", f"idx_{idx}")
        print(f"\n[{pos}/{len(mismatched_indices)}] Repairing story index {idx} (Story ID: {story_id})...")
        print(f"    Current premises-NL: {len(sample.get('premises-NL', []))} | premises-FOL: {len(sample.get('premises-FOL', []))}")
        
        success, repaired = repair_sample(llm_client, sample, idx)
        if success:
            dataset[idx] = repaired
            success_count += 1
        else:
            print(f"    [FAILED] Could not repair story index {idx}.")
            fail_count += 1
            
        time.sleep(2)  # Polite API delay

    # Save results
    if success_count > 0:
        print(f"\nSaving {success_count} repaired stories to {input_file.name}...")
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print("Saved successfully.")
    else:
        print("\nNo stories were repaired. Input file not modified.")

    print("\n" + "=" * 80)
    print("REPAIR WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"Total processed:   {len(mismatched_indices)}")
    print(f"Total succeeded:   {success_count}")
    print(f"Total failed:      {fail_count}")
    print("=" * 80)

if __name__ == "__main__":
    main()
