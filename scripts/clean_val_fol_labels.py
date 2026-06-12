import json
import os
import sys
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

# Add project root to path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from scripts.validate_dataset_syntax import validate_sample_fol

SYSTEM_PROMPT = """You convert natural-language premises into first-order logic formulas.
Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.
You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.

ALLOWED OPERATORS:
AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists

STRICT RULES & CONSTRAINTS:
1. QUANTIFIER RULES:
   - Quantifiers MUST only quantify ONE variable at a time and must be nested.
   - CORRECT: ForAll(x, ForAll(y, P(x, y)))
   - INCORRECT: ForAll([x, y], P(x, y)) or ForAll(x, y, P(x, y))

2. DOMAIN RESTRICTION RULE:
   - Restrict the domain of quantified variables to the relevant category.
   - E.g., "All students are happy" -> ForAll(x, Student(x) -> Happy(x))
   - Do NOT write ForAll(x, Happy(x)).
   - "No student who enjoys nature has free time" -> ForAll(x, Student(x) AND EnjoysNature(x) -> NOT FreeTime(x))

3. NO IMPLICATION UNDER EXISTENTIAL QUANTIFIERS:
   - Never use implication (->) under an existential quantifier (Exists). Always use conjunction (AND).
   - E.g., "There is a student who enjoys nature" -> Exists(x, Student(x) AND EnjoysNature(x))
   - Do NOT write Exists(x, Student(x) -> EnjoysNature(x)).

4. NUMERICAL ATTRIBUTES & COMPARISONS:
   - Represent numerical attributes (e.g., age, score, GPA, duration, credits) as functions mapping to a number, and compare using operators (=, !=, >=, <=, >, <).
   - E.g., "John has a GPA of 3.8" -> GPA(john) = 3.8
   - E.g., "GPA is at least 3.5" -> ForAll(x, GPA(x) >= 3.5 -> ...)
   - Do NOT use binary predicates like GPA(john, 3.8) or hardcoded properties in predicate names like Seats300(x). Write Seats(x) > 300 instead.

5. EXACT FACT TRANSLATION (LITERAL TRANSLATION):
   - Translate facts about individuals exactly as facts, not as universal rules.
   - E.g., "Alex has a valid membership card" -> HasValidMembershipCard(alex) or HasCard(alex). Do NOT translate this into a general rule if it only concerns Alex.
   - Only translate general rules (like "All members must have cards") into universal rules (ForAll).

6. PARENTHESES & ARITY:
   - Ensure every open parenthesis '(' has a matching close parenthesis ')'.
   - A predicate or function always has the exact same name casing and number of arguments across all formulas in the sample.
   - Use empty parentheses '()' for zero-arity predicates if any.

OUTPUT FORMAT:
Return ONLY a valid JSON list of strings (the FOL formulas). Do not include markdown formatting or explanation.
"""

USER_PROMPT_TEMPLATE = """Convert the following {num_premises} premises into first-order logic formulas, matching 1-to-1 in length.

Premises-NL:
{premises_nl}

Return the JSON list of exactly {num_premises} strings."""

FEEDBACK_TEMPLATE = """Your previous translation failed validation with the following error:
{error_msg}

Please correct the formulas and return a valid JSON list of exactly {num_premises} strings."""

def clean_json_markdown(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    return text

def translate_sample(api_key, premises_nl, max_retries=3):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    num_premises = len(premises_nl)
    nl_formatted = "\n".join(f"{i+1}. {p}" for i, p in enumerate(premises_nl))
    user_prompt = USER_PROMPT_TEMPLATE.format(num_premises=num_premises, premises_nl=nl_formatted)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    last_request_time = 0.0
    
    for turn in range(1, max_retries + 1):
        # Format conversation prompt for Gemini REST API
        prompt_full = SYSTEM_PROMPT + "\n\n"
        for msg in messages:
            role_header = "User:" if msg["role"] == "user" else "Assistant:"
            prompt_full += f"\n{role_header}\n{msg['content']}\n"
        prompt_full += "\nAssistant:\n"
        
        payload = {
            "contents": [{"parts": [{"text": prompt_full}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        # Force RPM limits
        elapsed = time.time() - last_request_time
        if elapsed < 4.0:
            time.sleep(4.0 - elapsed)
        last_request_time = time.time()
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                resp_json = response.json()
                resp_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                clean_text = clean_json_markdown(resp_text)
                fol_list = json.loads(clean_text)
                
                if not isinstance(fol_list, list) or len(fol_list) != num_premises:
                    error_msg = f"Length mismatch: Expected {num_premises} formulas, but got {len(fol_list)}."
                    print(f"      - Turn {turn}: {error_msg}")
                    messages.append({"role": "assistant", "content": clean_text})
                    messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, num_premises=num_premises)})
                    continue
                
                # Validate with Z3 parser
                # Convert formulas to string
                fol_str_list = [str(x).strip() for x in fol_list]
                is_valid, err = validate_sample_fol(fol_str_list)
                if not is_valid:
                    error_msg = f"Z3 parser error: {err}"
                    print(f"      - Turn {turn}: {error_msg}")
                    messages.append({"role": "assistant", "content": clean_text})
                    messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, num_premises=num_premises)})
                    continue
                
                # Success!
                return True, fol_str_list
                
            elif response.status_code == 429:
                print("      - Rate limited. Waiting 30s...")
                time.sleep(30)
                # Retry this turn
                continue
            else:
                print(f"      - HTTP error {response.status_code}: {response.text}")
                time.sleep(5)
        except Exception as e:
            print(f"      - Exception occurred: {e}")
            time.sleep(5)
            
    return False, None

def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
        
    data_dir = root_dir / "data" / "processed"
    augmented_path = data_dir / "logic_merged_valid_augmented.json"
    original_path = data_dir / "logic_merged_valid.json"
    
    if not augmented_path.exists():
        print(f"Error: {augmented_path} not found.")
        sys.exit(1)
        
    print(f"Loading augmented validation samples...")
    with open(augmented_path, "r", encoding="utf-8") as f:
        augmented_data = json.load(f)
        
    val_samples = [item for item in augmented_data if item.get("split") == "val"]
    print(f"Found {len(val_samples)} validation samples to clean.")
    
    corrections = {}
    for idx, item in enumerate(val_samples, 1):
        example_id = item.get("example_id")
        premises_nl = item.get("premises-NL", [])
        original_fol = item.get("premises-FOL", [])
        
        # Check if the validation sample has a fact-rule mismatch or other known mismatch
        # We can clean all of them to be 100% consistent with the prompt instructions
        print(f"[{idx}/{len(val_samples)}] Cleaning FOL for example {example_id}...")
        success, cleaned_fol = translate_sample(api_key, premises_nl)
        if success:
            print(f"  -> SUCCESS! Cleaned formulas:")
            for p_fol in cleaned_fol:
                print(f"     - {p_fol}")
            corrections[example_id] = cleaned_fol
        else:
            print(f"  -> FAILED to clean formulas for example {example_id}. Keeping original.")
            
    # Apply corrections and write to files
    if corrections:
        # Update logic_merged_valid_augmented.json
        for item in augmented_data:
            eid = item.get("example_id")
            if eid in corrections:
                item["premises-FOL"] = corrections[eid]
                item.pop("validation_error", None)
                
        with open(augmented_path, "w", encoding="utf-8") as f:
            json.dump(augmented_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved updated augmented dataset to: {augmented_path.name}")
        
        # Update logic_merged_valid.json
        if original_path.exists():
            with open(original_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)
                
            for item in original_data:
                eid = item.get("example_id")
                # Wait, original data example_id might end in _canonical, or be identical to eid
                # Let's clean the canonical suffix to match if needed
                match_eid = eid
                if not match_eid:
                    continue
                # Match either exact ID or canonical counterpart
                matched = False
                for k_eid in corrections:
                    if k_eid == match_eid or k_eid.split("_canonical")[0] == match_eid or match_eid.split("_canonical")[0] == k_eid:
                        item["premises-FOL"] = corrections[k_eid]
                        item.pop("validation_error", None)
                        matched = True
                        break
                        
            with open(original_path, "w", encoding="utf-8") as f:
                json.dump(original_data, f, indent=2, ensure_ascii=False)
            print(f"Saved updated original dataset to: {original_path.name}")
            
    print("Label cleaning process completed successfully.")

if __name__ == "__main__":
    main()
