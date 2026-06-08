import json
import os
import sys
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

# Add project root to path
root = Path(__file__).resolve().parents[3]
sys.path.append(str(root))

def clean_json_markdown(text: str) -> str:
    """Strip markdown code block wrappers from JSON string."""
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    return text

def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in environment or .env file.")
        sys.exit(1)
        
    data_dir = root / "data" / "processed"
    augmented_path = data_dir / "logic_merged_valid_augmented.json"
    original_path = data_dir / "logic_merged_valid.json"
    
    if not augmented_path.exists():
        print(f"Error: {augmented_path} not found.")
        sys.exit(1)
        
    print(f"Loading augmented dataset from {augmented_path}...")
    with open(augmented_path, "r", encoding="utf-8") as f:
        augmented_data = json.load(f)
        
    # Get all validation samples (where split == "val")
    val_samples = [item for item in augmented_data if item.get("split") == "val"]
    print(f"Found {len(val_samples)} validation samples to clean.")
    
    if not val_samples:
        print("No validation samples found in augmented dataset.")
        return
        
    # Setup API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    print("\nStarting LLM-based label verification & correction...")
    print("=" * 60)
    
    corrections = {}
    last_request_time = 0.0
    
    for idx, item in enumerate(val_samples, 1):
        example_id = item.get("example_id")
        premises_nl = item.get("premises-NL", [])
        question = item.get("question", "")
        original_ans = item.get("answer", "")
        explanation = item.get("explanation")
        
        # Resume capability: if already verified in a previous run (explanation is a non-empty string)
        if isinstance(explanation, str) and explanation.strip() and explanation.strip().lower() != "none":
            print(f"[{idx}/{len(val_samples)}] Sample {example_id} already verified: '{original_ans}'")
            corrections[example_id] = {
                "answer": original_ans,
                "explanation": explanation
            }
            continue
            
        premises_str = "\n".join(f"- {p}" for p in premises_nl)
        
        prompt = (
            "You are an expert in mathematical logic and logical reasoning.\n"
            "We have a logical reasoning dataset containing natural language premises, a question, and a candidate answer.\n"
            "However, some of the candidate answers in the dataset are logically incorrect due to annotation errors or incorrect dataset perturbation (such as changing the story but leaving logical loopholes, or violating strict implications).\n\n"
            "Your task is to:\n"
            "1. Read the natural language premises and the question.\n"
            "2. Determine if the question is a True/False/Unknown question or a Multiple Choice Question (A, B, C, D).\n"
            "3. Logically deduce the correct answer strictly based on the premises (assuming the open-world assumption, i.e., classic first-order logic).\n"
            "   - If it is a multiple-choice question, select the single best capital letter choice (A, B, C, or D). If none of the options is logically supported or if there is insufficient info, select 'Unknown'.\n"
            "   - If it is a True/False/Unknown question, answer with 'True', 'False', or 'Unknown'.\n"
            "4. Provide a very brief, 1-2 sentence explanation of your deduction.\n\n"
            "Input:\n"
            f"Premises:\n{premises_str}\n\n"
            f"Question:\n{question}\n\n"
            f"Original Answer in Dataset:\n{original_ans}\n\n"
            "Respond in the following JSON format:\n"
            "{\n"
            '  "corrected_answer": "<your corrected answer, e.g. A, B, C, D, True, False, or Unknown>",\n'
            '  "explanation": "<your brief explanation>"\n'
            "}\n"
            "Return ONLY the JSON object. Do not add any extra text or markdown formatting."
        )
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        print(f"[{idx}/{len(val_samples)}] Verifying sample {example_id}...")
        
        success = False
        retry_count = 0
        while not success and retry_count < 5:
            try:
                # Force rate limit spacing (15 RPM -> at least 5.0s between start of requests)
                elapsed = time.time() - last_request_time
                if elapsed < 5.0:
                    time.sleep(5.0 - elapsed)
                last_request_time = time.time()
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    resp_json = response.json()
                    resp_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    clean_text = clean_json_markdown(resp_text)
                    result = json.loads(clean_text)
                    
                    corrected_ans = result.get("corrected_answer")
                    explanation = result.get("explanation")
                    
                    if corrected_ans:
                        corrections[example_id] = {
                            "answer": corrected_ans,
                            "explanation": explanation
                        }
                        if corrected_ans.strip().lower() != str(original_ans).strip().lower():
                            print(f"  -> CORRECTED: '{original_ans}' -> '{corrected_ans}'")
                            print(f"  -> Explanation: {explanation}")
                        else:
                            print(f"  -> Verified correct: '{original_ans}'")
                        success = True
                    else:
                        print("  -> Error: Response missing corrected_answer field.")
                        retry_count += 1
                elif response.status_code == 429:
                    sleep_time = 60.0
                    try:
                        resp_json = response.json()
                        error_details = resp_json.get("error", {}).get("details", [])
                        for detail in error_details:
                            if "RetryInfo" in detail.get("@type", ""):
                                delay_str = detail.get("retryDelay", "60s")
                                match = re.match(r"^([0-9.]+)", delay_str)
                                if match:
                                    sleep_time = float(match.group(1))
                                    break
                    except Exception:
                        pass
                    
                    # If detail parsing failed, try regex on body text
                    if sleep_time == 60.0:
                        match = re.search(r"Please retry in ([0-9.]+)s", response.text)
                        if match:
                            sleep_time = float(match.group(1))
                            
                    print(f"  -> [Rate Limit 429] Exceeded quota. Sleeping for {sleep_time + 2.0:.2f} seconds before retrying...")
                    time.sleep(sleep_time + 2.0)
                    # Note: We do NOT increment retry_count here, so we will retry this request until successful
                else:
                    print(f"  -> HTTP Error {response.status_code}: {response.text}")
                    retry_count += 1
                    time.sleep(5)
            except Exception as e:
                print(f"  -> Connection/Parsing error: {e}")
                retry_count += 1
                time.sleep(5)
                
        if not success:
            print(f"  -> Failed to verify sample {example_id} after retries.")
            
    print("\n" + "=" * 60)
    print(f"Completed verification. Found {len(corrections)} successfully processed samples.")
    
    # Apply corrections to both datasets
    if corrections:
        # 1. Update logic_merged_valid_augmented.json
        updated_augmented_count = 0
        for item in augmented_data:
            eid = item.get("example_id")
            if eid in corrections:
                item["answer"] = corrections[eid]["answer"]
                item["explanation"] = corrections[eid]["explanation"]
                updated_augmented_count += 1
                
        with open(augmented_path, "w", encoding="utf-8") as f:
            json.dump(augmented_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated {updated_augmented_count} samples in {augmented_path.name}")
        
        # 2. Update logic_merged_valid.json (if it exists)
        if original_path.exists():
            with open(original_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)
                
            updated_original_count = 0
            for item in original_data:
                eid = item.get("example_id")
                if eid in corrections:
                    item["answer"] = corrections[eid]["answer"]
                    item["explanation"] = corrections[eid]["explanation"]
                    updated_original_count += 1
                    
            with open(original_path, "w", encoding="utf-8") as f:
                json.dump(original_data, f, indent=2, ensure_ascii=False)
            print(f"Successfully updated {updated_original_count} samples in {original_path.name}")
            
    print("Label cleaning completed successfully!")

if __name__ == "__main__":
    main()
