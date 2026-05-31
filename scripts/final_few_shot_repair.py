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
    print("FEW-SHOT SPECIALIZED LOGIC REPAIR FOR REMAINING 25 SAMPLES")
    print("Uses targeted exemplars to guide Qwen3-235B on exact qualitative mapping.")
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
Your task is to correct the 'premises-FOL' field of a single invalid logical sample.
Our logic parser runs a strict subset of First-Order Logic (FOL) in Python and validates them using the Z3 SMT solver.

### STRICT PARSER AND GRAMMAR RULES:
1. QUANTIFIER RULES:
   - Quantifiers MUST only quantify ONE variable at a time and must be nested.
   - CORRECT: ForAll(x, ForAll(y, P(x, y)))
   - INCORRECT: ForAll([x, y], P(x, y)) or ForAll(x, y, P(x, y)) or ForAll(x AND y, P(x, y)) - Never use list brackets [] in ForAll or Exists!

2. LOGICAL CONNECTIVES:
   - Must be strictly UPPERCASE: AND, OR, NOT, ->, <->.
   - CORRECT: P(x) -> (Q(x) AND R(x))

3. NO MATHEMATICAL OPERATORS OR EXPRESSIONS:
   - The parser does NOT support division (/), multiplication (*), or exponentiation (^).
   - You MUST represent all mathematical equations, divisions, percentages, and multiplications qualitatively using standard uninterpreted predicates, functions, or constants.

### FEW-SHOT TARGETED EXEMPLARS:
- NL: "Students must accumulate at least 65% of the total credits of their training program."
  FOL: "ForAll(s, (EligibleForInternship(s) <-> AccumulatedCredits(s) >= RequiredInternshipCredits(Program(s))))"
- NL: "Phong scored 95% on exams on 25/3/2025."
  FOL: "PhongExamScore(Phong) AND ExamDate(Phong, date_25_3_2025)"
- NL: "Phong has an average semester score of 2.3."
  FOL: "AverageSemesterScore(Phong) = score_2_3"
- NL: "Scores are calculated based on a weighted average of exams (60%) and projects (40%)."
  FOL: "ForAll(s, WeightedAverageCalculation(s))"
- NL: "Students ranked below Fair must attend a study skills workshop."
  FOL: "ForAll(s, (Ranking_Average(s) OR Ranking_Weak(s) OR Ranking_Poor(s) -> MustAttendWorkshop(s)))"
- NL: "Accumulated credits must be less than 2 * M_regular."
  FOL: "ForAll(s, AccumulatedCredits(s) < double_M_regular)"
- NL: "If internships are unpaid, students cannot complete them without financial support."
  FOL: "ForAll(s, (UnpaidInternships AND NOT financial_support(s) -> NOT internship(s)))"
- NL: "Lan has both health insurance and accident insurance."
  FOL: "health_insurance(Lan) AND accident_insurance(Lan)"
- NL: "Ebbinghaus forgetting curve formula: R = e^(-t/S)"
  FOL: "ForAll(s, ForAll(t, ForAll(S, ForgettingCurveRelation(s, t, S))))"

4. NO SINGLE QUOTES FOR CONSTANTS:
   - Do NOT wrap constants or values (like grades a+, b+, c++ or names) in single quotes (e.g. do not write 'a+', 'c++'). Z3 treats single-quoted values as String sort, causing a sort mismatch with uninterpreted domain elements (default sort U).
   - Rename them to clean alphanumeric identifiers:
     - E.g. write Grade(aplus) instead of Grade('a+').

5. RESOLVING SORT MISMATCHES WITH NUMERICAL VALUES:
   - Avoid variable sort collisions: A variable cannot be both sort U and sort Int/Real.
   - If a variable is compared to a number, represent the predicate functionally (e.g. AccumulatedCredits(s) >= double_M_regular) or convert it to a qualitative predicate (e.g. MeetsCreditRequirement(s)).
   - Do not pass raw numbers as arguments to uninterpreted predicates (e.g. EstablishedIn(x, year2000) instead of EstablishedIn(x, 2000)).

6. PARENTHESES & ARITY:
   - Ensure every open parenthesis '(' has a matching close parenthesis ')'.
   - Avoid spaces before argument lists: write P(x) NOT P (x).
   - Ensure a predicate or function always has the exact same name casing and number of arguments across all premises in the sample. E.g. do not mix P(x) and P(x, y).

Provide your corrected sample as a single valid JSON object matching our unified schema. Return JSON only, without any markdown formatting or extra text.
"""

    user_prompt_template = """Analyze and correct the following invalid logical sample under strict parser and grammar rules.
Convert all complex math, divisions (/), and multiplications (*) into qualitative predicates, functions, or uninterpreted constants as specified in the rules!

Invalid sample:
{sample_json}

Return the strict JSON object of the corrected sample only.
"""

    total_successful = 0
    total_failed = 0
    start_time = time.time()

    for idx, sample in enumerate(invalid_samples, start=1):
        ex_id = sample["example_id"]
        source = sample["dataset_source"]
        orig_error = sample["validation_error"]

        print(f"\n" + "=" * 80)
        print(f"SAMPLE {idx}/{len(invalid_samples)} | ID: {ex_id} | Source: {source}")
        print(f"Current Z3 Error: {orig_error}")
        print("=" * 80)

        # Construct user prompt
        user_prompt = user_prompt_template.format(
            sample_json=json.dumps(sample, indent=2, ensure_ascii=False)
        )

        print("Sending request to Qwen3-235B...")
        try:
            response_text = llm_client.generate_text(user_prompt, system_prompt=system_prompt, max_new_tokens=2048)
        except Exception as e:
            print(f"  - LLM Call failed: {e}")
            total_failed += 1
            continue

        # Parse response
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
            print(f"  - Failed to parse JSON: {e}")
            total_failed += 1
            continue

        if not isinstance(repaired_sample, dict):
            print("  - Error: Response is not a JSON object.")
            total_failed += 1
            continue

        rep_formulas = repaired_sample.get("premises-FOL", [])

        # Quick post-processing cleanup to ensure 100% quantifier compliance
        cleaned_formulas = []
        for f in rep_formulas:
            # Replace list quantifiers ForAll([s], ...) -> ForAll(s, ...)
            f_clean = re.sub(r"\b(ForAll|Exists)\(\s*\[\s*([a-zA-Z_]\w*)\s*\]\s*,", r"\1(\2,", f)
            # Replace multiple quantifiers ForAll([x, y], ...) -> ForAll(x, ForAll(y, ...))
            match_multi = re.search(r"\b(ForAll|Exists)\(\s*\[\s*([a-zA-Z_]\w*)\s*,\s*([a-zA-Z_]\w*)\s*\]\s*,", f_clean)
            if match_multi:
                q, v1, v2 = match_multi.groups()
                f_clean = re.sub(r"\b(ForAll|Exists)\(\s*\[\s*[a-zA-Z_]\w*\s*,\s*[a-zA-Z_]\w*\s*\]\s*,", f"{q}({v1}, {q}({v2},", f_clean) + ")"
            cleaned_formulas.append(f_clean)

        repaired_sample["premises-FOL"] = cleaned_formulas

        # Quick checks
        has_forbidden_chars = False
        forbidden_reasons = []
        for f in cleaned_formulas:
            if "/" in f:
                has_forbidden_chars = True
                forbidden_reasons.append(f"Contains division '/': {f}")
            if "*" in f:
                has_forbidden_chars = True
                forbidden_reasons.append(f"Contains multiplication '*': {f}")
            if "[" in f or "]" in f:
                has_forbidden_chars = True
                forbidden_reasons.append(f"Contains list brackets []: {f}")

        if has_forbidden_chars:
            print(f"  [REJECTED] Sample {ex_id}: Repair contains forbidden characters.")
            print("\n".join(forbidden_reasons))
            total_failed += 1
            continue

        is_valid, error_msg = validate_sample_fol(cleaned_formulas)

        if is_valid:
            print(f"  [SUCCESS] Sample {ex_id}: Successfully repaired! Z3 parsed perfectly.")
            repaired_sample.pop("validation_error", None)
            total_successful += 1

            # Save immediately to disk
            with open(valid_path, "r", encoding="utf-8") as f:
                valid_samples = json.load(f)
            with open(invalid_path, "r", encoding="utf-8") as f:
                current_invalid_samples = json.load(f)

            valid_samples.append(repaired_sample)
            updated_invalid = [s for s in current_invalid_samples if s["example_id"] != ex_id]

            try:
                with open(valid_path, "w", encoding="utf-8") as f:
                    json.dump(valid_samples, f, indent=2, ensure_ascii=False)
                with open(invalid_path, "w", encoding="utf-8") as f:
                    json.dump(updated_invalid, f, indent=2, ensure_ascii=False)
                print(f"    -> Merged {ex_id} to valid file (Total valid: {len(valid_samples)}, Total invalid: {len(updated_invalid)})")
            except Exception as e:
                print(f"    -> Error updating files: {e}")
        else:
            print(f"  [FAILED] Sample {ex_id}: Repair attempt failed Z3 validation.")
            print(f"    - New Z3 error:   {error_msg}")
            total_failed += 1

        # Politeness delay
        time.sleep(2)

    print("\n" + "=" * 80)
    print("FEW-SHOT SPECIALIZED REPAIR COMPLETED")
    print("=" * 80)
    print(f"Total processed: {len(invalid_samples)}")
    print(f"Successfully repaired: {total_successful}")
    print(f"Failed to repair:      {total_failed}")
    print(f"Execution time:        {time.time() - start_time:.2f} seconds")
    print("=" * 80)


if __name__ == "__main__":
    main()
