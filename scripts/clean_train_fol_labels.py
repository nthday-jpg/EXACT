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

SYSTEM_PROMPT_SINGLE = """You convert natural-language premises into first-order logic formulas.
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

SYSTEM_PROMPT_BATCH = """You convert natural-language premises into first-order logic (FOL) formulas.
You will be given a JSON list of logical reasoning samples to translate.
For each sample, convert its natural-language premises into parser-safe first-order logic formulas.

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
Return ONLY a valid JSON object where keys are the sample IDs and values are JSON lists of strings (the FOL formulas). Do not include markdown formatting or explanation.
Example:
{
  "10": [
    "Holds(suduva_marijampole, lithuanian_supercup)",
    "SoccerTeam(suduva_marijampole)"
  ]
}
"""

USER_PROMPT_SINGLE_TEMPLATE = """Convert the following {num_premises} premises into first-order logic formulas, matching 1-to-1 in length.

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

def translate_single_sample(api_key, premises_nl, max_retries=3):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    num_premises = len(premises_nl)
    nl_formatted = "\n".join(f"{i+1}. {p}" for i, p in enumerate(premises_nl))
    user_prompt = USER_PROMPT_SINGLE_TEMPLATE.format(num_premises=num_premises, premises_nl=nl_formatted)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_SINGLE},
        {"role": "user", "content": user_prompt}
    ]
    
    for turn in range(1, max_retries + 1):
        payload = {
            "model": "google/gemini-2.5-flash",
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                resp_json = response.json()
                resp_text = resp_json["choices"][0]["message"]["content"]
                clean_text = clean_json_markdown(resp_text)
                fol_list = json.loads(clean_text)
                
                if not isinstance(fol_list, list) or len(fol_list) != num_premises:
                    error_msg = f"Length mismatch: Expected {num_premises} formulas, but got {len(fol_list)}."
                    messages.append({"role": "assistant", "content": clean_text})
                    messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, num_premises=num_premises)})
                    continue
                
                fol_str_list = [str(x).strip() for x in fol_list]
                is_valid, err = validate_sample_fol(fol_str_list)
                if not is_valid:
                    error_msg = f"Z3 parser error: {err}"
                    messages.append({"role": "assistant", "content": clean_text})
                    messages.append({"role": "user", "content": FEEDBACK_TEMPLATE.format(error_msg=error_msg, num_premises=num_premises)})
                    continue
                
                return True, fol_str_list
            elif response.status_code == 429:
                print("      [Single] Rate limited on OpenRouter. Waiting 10s...")
                time.sleep(10)
            else:
                print(f"      [Single] OpenRouter HTTP error {response.status_code}: {response.text}")
                time.sleep(3)
        except Exception as e:
            print(f"      [Single] Exception: {e}")
            time.sleep(3)
            
    return False, None

def translate_batch(api_key, batch_samples):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Construct batch payload with count constraints!
    batch_json = []
    for s in batch_samples:
        batch_json.append({
            "id": s["example_id"],
            "expected_number_of_formulas": len(s["premises-NL"]),
            "premises": s["premises-NL"]
        })
        
    user_prompt = (
        f"Translate the following samples:\n{json.dumps(batch_json, indent=2)}\n\n"
        "Return a valid JSON object mapping each sample ID to its list of FOL formulas. "
        "The output list of formulas for each sample MUST have the exact length specified by 'expected_number_of_formulas'."
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_BATCH},
        {"role": "user", "content": user_prompt}
    ]
    
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            resp_json = response.json()
            resp_text = resp_json["choices"][0]["message"]["content"]
            clean_text = clean_json_markdown(resp_text)
            batch_result = json.loads(clean_text)
            return True, batch_result
        elif response.status_code == 429:
            print("      [Batch] Rate limited on OpenRouter. Waiting 10s...")
            time.sleep(10)
            return False, "Rate limited"
        else:
            return False, f"OpenRouter HTTP error {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def main():
    load_dotenv()
    api_key = os.environ.get("OPEN_ROUTER_KEY")
    if not api_key:
        print("Error: OPEN_ROUTER_KEY is not set.")
        sys.exit(1)
        
    data_dir = root_dir / "data" / "processed"
    augmented_path = data_dir / "logic_merged_valid_augmented.json"
    original_path = data_dir / "logic_merged_valid.json"
    corrections_path = data_dir / "clean_train_corrections.json"
    
    if not augmented_path.exists():
        print(f"Error: {augmented_path} not found.")
        sys.exit(1)
    if not original_path.exists():
        print(f"Error: {original_path} not found.")
        sys.exit(1)
        
    # 1. Load validation example IDs from augmented file
    print("Loading augmented dataset split information...")
    with open(augmented_path, "r", encoding="utf-8") as f:
        augmented_data = json.load(f)
        
    val_ids = set()
    for item in augmented_data:
        if item.get("split") == "val":
            eid = item.get("example_id", "").replace("_canonical", "")
            val_ids.add(eid)
            
    print(f"Found {len(val_ids)} validation sample IDs (already cleaned).")
    
    # 2. Load original dataset to identify training samples
    print("Loading original dataset logic_merged_valid.json...")
    with open(original_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)
        
    train_samples = []
    for item in original_data:
        eid = item.get("example_id", "").replace("_canonical", "")
        if eid not in val_ids:
            train_samples.append(item)
            
    print(f"Found {len(train_samples)} training samples total in logic_merged_valid.json.")
    
    # 3. Deduplicate training samples by premises-NL to find unique stories
    unique_stories = {}
    for item in train_samples:
        nl_list = item.get("premises-NL", [])
        if not nl_list:
            continue
        serialized_nl = "\n".join(nl_list)
        if serialized_nl not in unique_stories:
            unique_stories[serialized_nl] = {
                "example_id": item["example_id"],
                "premises-NL": nl_list,
                "items": []
            }
        unique_stories[serialized_nl]["items"].append(item)
        
    unique_story_list = list(unique_stories.values())
    print(f"Deduplicated training samples into {len(unique_story_list)} unique logical stories.")
    
    # 4. Load existing corrections from checkpoints file
    corrections = {}
    if corrections_path.exists():
        try:
            with open(corrections_path, "r", encoding="utf-8") as f:
                corrections = json.load(f)
            print(f"Loaded {len(corrections)} translated stories from checkpoints file {corrections_path.name}")
        except Exception as e:
            print(f"Warning: Failed to load checkpoints: {e}")
            
    # Filter stories that still need translation
    stories_to_translate = [s for s in unique_story_list if "\n".join(s["premises-NL"]) not in corrections]
    print(f"Already translated: {len(unique_story_list) - len(stories_to_translate)} stories. Remaining to translate: {len(stories_to_translate)}")
    
    # 5. Clean remaining unique training stories in batches of 5
    batch_size = 5
    total_stories = len(stories_to_translate)
    last_request_time = 0.0
    
    idx = 0
    while idx < total_stories:
        batch_samples = stories_to_translate[idx : idx + batch_size]
        print(f"\nProcessing batch {idx // batch_size + 1}/{(total_stories + batch_size - 1) // batch_size} (Stories {idx+1} to {min(idx+batch_size, total_stories)} of {total_stories} remaining)...")
        
        # Enforce rate limit (Using OpenRouter -> we can lower the sleep to 1.0 second!)
        elapsed = time.time() - last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        last_request_time = time.time()
        
        success, batch_result = translate_batch(api_key, batch_samples)
        
        batch_failed_samples = []
        if success:
            print("  Batch API call succeeded. Validating Z3 syntax and lengths...")
            for s in batch_samples:
                s_id = s["example_id"]
                s_nl = s["premises-NL"]
                serialized_nl = "\n".join(s_nl)
                
                # Check if id in response
                if s_id not in batch_result:
                    print(f"    - ID {s_id} missing from batch response. Falling back to single.")
                    batch_failed_samples.append(s)
                    continue
                    
                fol_list = batch_result[s_id]
                if not isinstance(fol_list, list) or len(fol_list) != len(s_nl):
                    print(f"    - ID {s_id} has list length mismatch ({len(fol_list) if isinstance(fol_list, list) else 'not a list'} vs {len(s_nl)}). Falling back.")
                    batch_failed_samples.append(s)
                    continue
                    
                fol_str_list = [str(x).strip() for x in fol_list]
                is_valid, err = validate_sample_fol(fol_str_list)
                if not is_valid:
                    print(f"    - ID {s_id} Z3 validation failed: {err}. Falling back.")
                    batch_failed_samples.append(s)
                    continue
                    
                # Success for this sample!
                corrections[serialized_nl] = fol_str_list
        else:
            print(f"  Batch API call failed: {batch_result}. Falling back to translating batch individually.")
            batch_failed_samples = batch_samples
            
        # Fallback to single-sample translation for failed items
        if batch_failed_samples:
            print(f"  Translating {len(batch_failed_samples)} failed samples in fallback mode...")
            for s in batch_failed_samples:
                s_nl = s["premises-NL"]
                serialized_nl = "\n".join(s_nl)
                
                # Rate limit for single calls
                elapsed = time.time() - last_request_time
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                last_request_time = time.time()
                
                print(f"    Translating sample {s['example_id']} individually...")
                s_success, fol_str_list = translate_single_sample(api_key, s_nl)
                if s_success:
                    print(f"      -> Success!")
                    corrections[serialized_nl] = fol_str_list
                else:
                    print(f"      -> FAILED to translate {s['example_id']}. Keeping original.")
                    
        # Checkpoint: save corrections incrementally to disk
        try:
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump(corrections, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  Warning: Failed to save checkpoint: {e}")
            
        idx += batch_size
        
    # 6. Apply corrections back to original dataset
    updated_count = 0
    for item in original_data:
        nl_list = item.get("premises-NL", [])
        if not nl_list:
            continue
        serialized_nl = "\n".join(nl_list)
        if serialized_nl in corrections:
            item["premises-FOL"] = corrections[serialized_nl]
            item.pop("validation_error", None)
            updated_count += 1
            
    print(f"\nCompleted translation. Updated FOL formulas for {updated_count} samples in original list.")
    
    # Save the updated original dataset
    with open(original_path, "w", encoding="utf-8") as f:
        json.dump(original_data, f, indent=2, ensure_ascii=False)
    print(f"Successfully saved updated training formulas to: {original_path}")
    
    # Clean up checkpoint file after successful completion
    if corrections_path.exists():
        try:
            corrections_path.unlink()
            print("Cleaned up temporary checkpoint file.")
        except Exception:
            pass

if __name__ == "__main__":
    main()
