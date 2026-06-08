import json
import os
import sys
import time
import random
import requests
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)

    root = Path(__file__).resolve().parents[1]
    augmented_path = root / "data" / "processed" / "logic_merged_valid_augmented.json"
    
    if not augmented_path.exists():
        print(f"Error: {augmented_path} not found.")
        sys.exit(1)
        
    with open(augmented_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    val_samples = [item for item in data if item.get("split") == "val"]
    print(f"Loaded {len(val_samples)} validation samples.")
    
    # Select 10 random samples
    random.seed(time.time()) # Keep it random as requested
    selected_samples = random.sample(val_samples, min(10, len(val_samples)))
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    report_content = "# Translation Quality Inspection Report\n\n"
    report_content += "Evaluated 10 random validation samples from the dataset using Gemini 3.1 Flash Lite.\n\n"
    
    print("\nStarting translation inspection using Gemini 3.1 Flash Lite...")
    print("=" * 60)
    
    last_request_time = 0.0
    for idx, item in enumerate(selected_samples, 1):
        example_id = item.get("example_id")
        premises_nl = item.get("premises-NL", [])
        premises_fol = item.get("premises-FOL", [])
        
        nl_content = "\n".join(f"{i}. {p}" for i, p in enumerate(premises_nl, start=1))
        fol_content = "\n".join(f"{i}. {f}" for i, f in enumerate(premises_fol, start=1))
        
        prompt = (
            "You are an expert in mathematical logic, first-order logic (FOL), and natural language processing.\n"
            "Evaluate whether the following natural language premises have been correctly translated into first-order logic formulas.\n\n"
            "Input:\n"
            f"Premises (NL):\n{nl_content}\n\n"
            f"Premises (FOL):\n{fol_content}\n\n"
            "Instructions:\n"
            "1. For each premise pair, state whether the translation is mathematically 'Correct' or has 'Issues' (e.g. wrong variables, mismatch in predicates, quantifier errors).\n"
            "2. Provide a brief explanation for any issues identified.\n"
            "3. Conclude with a final verdict for this sample: 'Accurate', 'Minor Mismatches', or 'Inaccurate'.\n\n"
            "Respond in a clean Markdown format. Keep explanations concise."
        )
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"thinkingConfig": {"thinkingBudget": 1024}}
        }
        
        # Rate limit spacing (5.0s)
        elapsed = time.time() - last_request_time
        if elapsed < 5.0:
            time.sleep(5.0 - elapsed)
        last_request_time = time.time()
        
        print(f"[{idx}/10] Evaluating sample {example_id}...")
        
        success = False
        retry_count = 0
        while not success and retry_count < 3:
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    resp_json = response.json()
                    resp_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    
                    sample_report = f"## Sample {example_id} (Evaluation {idx}/10)\n\n"
                    sample_report += f"**Premises (NL):**\n```\n{nl_content}\n```\n\n"
                    sample_report += f"**Premises (FOL):**\n```\n{fol_content}\n```\n\n"
                    sample_report += f"**LLM Evaluation:**\n\n{resp_text}\n\n"
                    sample_report += "---\n\n"
                    
                    report_content += sample_report
                    print("  -> Completed evaluation.")
                    success = True
                elif response.status_code == 429:
                    print("  -> Rate limited (429). Sleeping 30s...")
                    time.sleep(30.0)
                    last_request_time = time.time()
                else:
                    print(f"  -> API Error {response.status_code}. Retrying...")
                    retry_count += 1
                    time.sleep(5)
            except Exception as e:
                print(f"  -> Connection/parsing error: {e}")
                retry_count += 1
                time.sleep(5)
                
    report_path = root / "scratch" / "translation_inspection_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("\n" + "=" * 60)
    print(f"Inspection completed successfully! Report saved to {report_path}")

if __name__ == "__main__":
    main()
