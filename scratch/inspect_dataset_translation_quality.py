import json
import os
import sys
import time
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def clean_json_markdown(text: str) -> str:
    text = text.strip()
    # Strip <think>...</think> blocks if present
    text = re.sub(r"<\s*think\s*>.*?<\s*/\s*think\s*>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    return text

def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)

    root = Path(__file__).resolve().parents[1]
    dataset_path = root / "data" / "processed" / "logic_merged_valid_augmented.json"
    partial_results_path = root / "scratch" / "translation_inspections_partial.json"
    output_problems_path = root / "scratch" / "problematic_translation_samples.json"
    report_path = root / "scratch" / "translation_quality_report.md"
    
    if not dataset_path.exists():
        print(f"Error: {dataset_path} not found.")
        sys.exit(1)
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} total samples from dataset.")

    # Load existing progress if any
    evaluated_results = {}
    if partial_results_path.exists():
        try:
            with open(partial_results_path, "r", encoding="utf-8") as f:
                evaluated_results = json.load(f)
            print(f"Resuming: found {len(evaluated_results)} already evaluated samples.")
        except Exception as e:
            print(f"Warning: Failed to load partial progress: {e}. Starting fresh.")

    # Filter out samples already evaluated
    samples_to_evaluate = [item for item in data if item.get("example_id") not in evaluated_results]
    print(f"Samples remaining to evaluate: {len(samples_to_evaluate)}")

    if not samples_to_evaluate:
        print("All samples have already been evaluated!")
        generate_final_outputs(data, evaluated_results, output_problems_path, report_path)
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    batch_size = 50
    total_batches = (len(samples_to_evaluate) + batch_size - 1) // batch_size
    print(f"Evaluating in {total_batches} batches of {batch_size}...")

    last_request_time = 0.0

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(samples_to_evaluate))
        batch = samples_to_evaluate[start_idx:end_idx]

        print(f"\n--- Batch {batch_idx + 1}/{total_batches} (Samples {start_idx + 1} to {end_idx}) ---")

        # Format batch data for LLM
        batch_prompt_data = []
        for item in batch:
            nl_list = item.get("premises-NL", [])
            fol_list = item.get("premises-FOL", [])
            premises_paired = []
            for i, (nl, fol) in enumerate(zip(nl_list, fol_list), start=1):
                premises_paired.append({
                    "premise_index": i,
                    "nl": nl,
                    "fol": fol
                })
            batch_prompt_data.append({
                "example_id": item.get("example_id"),
                "premises": premises_paired
            })

        prompt = (
            "You are an expert in mathematical logic, first-order logic (FOL), and natural language processing.\n"
            "Evaluate whether the natural language (NL) premises have been correctly and accurately translated into the first-order logic (FOL) formulas for each sample.\n\n"
            "Input Batch of Samples (JSON format):\n"
            f"```json\n{json.dumps(batch_prompt_data, indent=2)}\n```\n\n"
            "Instructions:\n"
            "1. For each sample, analyze the translation of each premise.\n"
            "2. Decide the 'verdict' for the sample:\n"
            "   - 'Accurate': Every premise translation is logically correct and holds the exact same meaning.\n"
            "   - 'Minor Mismatches': Minor naming, capitalization, or formatting issues that do not change the core logical entailment, or minor typos.\n"
            "   - 'Inaccurate': Logic errors (e.g. wrong operators like using <-> instead of ->, wrong quantifier scopes, wrong variables, or missing conditions).\n"
            "3. Provide a list of 'issues' if the verdict is 'Minor Mismatches' or 'Inaccurate'. If 'Accurate', leave 'issues' empty.\n"
            "4. Return the evaluation STRICTLY as a JSON list of objects matching the following schema:\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"example_id\": \"...\",\n"
            "    \"verdict\": \"Accurate\" | \"Minor Mismatches\" | \"Inaccurate\",\n"
            "    \"issues\": [\"specific issue description 1\", \"specific issue description 2\"]\n"
            "  }\n"
            "]\n"
            "```\n"
            "Do not include any conversational explanation, markdown blocks outside the JSON list, or markdown format wrappers."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "thinkingConfig": {"thinkingBudget": 1024},
                "responseMimeType": "application/json"
            }
        }

        # Rate limit delay (5.0s)
        elapsed = time.time() - last_request_time
        if elapsed < 5.0:
            time.sleep(5.0 - elapsed)
        last_request_time = time.time()

        success = False
        retry_count = 0
        while not success and retry_count < 5:
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    resp_json = response.json()
                    resp_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    cleaned_text = clean_json_markdown(resp_text)
                    batch_evals = json.loads(cleaned_text)

                    # Store results
                    for eval_item in batch_evals:
                        eid = eval_item.get("example_id")
                        if eid:
                            evaluated_results[eid] = {
                                "verdict": eval_item.get("verdict", "Inaccurate"),
                                "issues": eval_item.get("issues", [])
                            }
                    
                    # Save progress to file
                    with open(partial_results_path, "w", encoding="utf-8") as f:
                        json.dump(evaluated_results, f, indent=2, ensure_ascii=False)
                    
                    print(f"  -> Successfully evaluated and saved batch progress.")
                    success = True

                elif response.status_code == 429:
                    print("  -> Rate limited (429). Sleeping 60s...")
                    time.sleep(60.0)
                    last_request_time = time.time()
                elif response.status_code == 503:
                    print("  -> Service unavailable (503). Sleeping 10s...")
                    time.sleep(10.0)
                else:
                    print(f"  -> API Error {response.status_code}. Retrying in 5s...")
                    retry_count += 1
                    time.sleep(5)
            except Exception as e:
                print(f"  -> Connection/parsing error: {e}. Retrying in 5s...")
                retry_count += 1
                time.sleep(5)
        
        if not success:
            print(f"Fatal: Failed to evaluate batch starting at index {start_idx} after multiple retries. Exiting.")
            sys.exit(1)

    print("\nAll evaluations completed successfully!")
    generate_final_outputs(data, evaluated_results, output_problems_path, report_path)

def generate_final_outputs(data, evaluated_results, output_problems_path, report_path):
    problematic_samples = []
    verdict_counts = {"Accurate": 0, "Minor Mismatches": 0, "Inaccurate": 0}
    
    for item in data:
        eid = item.get("example_id")
        eval_res = evaluated_results.get(eid)
        if eval_res:
            verdict = eval_res.get("verdict", "Accurate")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            
            if verdict in ("Minor Mismatches", "Inaccurate"):
                bad_item = item.copy()
                bad_item["translation_verdict"] = verdict
                bad_item["translation_issues"] = eval_res.get("issues", [])
                problematic_samples.append(bad_item)

    # Save output problems json
    with open(output_problems_path, "w", encoding="utf-8") as f:
        json.dump(problematic_samples, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(problematic_samples)} problematic translation samples to: {output_problems_path}")

    # Generate Markdown report
    total_evaluated = sum(verdict_counts.values())
    acc_pct = (verdict_counts["Accurate"] / total_evaluated * 100) if total_evaluated > 0 else 0
    min_pct = (verdict_counts["Minor Mismatches"] / total_evaluated * 100) if total_evaluated > 0 else 0
    inacc_pct = (verdict_counts["Inaccurate"] / total_evaluated * 100) if total_evaluated > 0 else 0

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 📝 Translation Quality Validation Report\n\n")
        f.write("This report validates the accuracy of Natural Language (NL) to First-Order Logic (FOL) translation across the entire tuning dataset.\n\n")
        
        f.write("## 📊 Summary Statistics\n\n")
        f.write(f"- **Total Samples Evaluated**: {total_evaluated}\n")
        f.write(f"- **Accurate**: {verdict_counts['Accurate']} ({acc_pct:.2f}%)\n")
        f.write(f"- **Minor Mismatches**: {verdict_counts['Minor Mismatches']} ({min_pct:.2f}%)\n")
        f.write(f"- **Inaccurate**: {verdict_counts['Inaccurate']} ({inacc_pct:.2f}%)\n\n")
        
        f.write("## ❌ Problematic Sample Highlights\n\n")
        for idx, sample in enumerate(problematic_samples[:50], start=1):
            f.write(f"### {idx}. Sample ID: `{sample.get('example_id')}`\n")
            f.write(f"- **Dataset Source**: `{sample.get('dataset_source')}`\n")
            f.write(f"- **Verdict**: `{sample.get('translation_verdict')}`\n")
            f.write("- **Issues Identified**:\n")
            for issue in sample.get("translation_issues", []):
                f.write(f"  - {issue}\n")
            f.write("\n")
            f.write("**NL Premises:**\n")
            for nl in sample.get("premises-NL", []):
                f.write(f"- {nl}\n")
            f.write("\n")
            f.write("**FOL Premises:**\n")
            f.write("```json\n")
            f.write(json.dumps(sample.get("premises-FOL", []), indent=2) + "\n")
            f.write("```\n\n")
            f.write("---\n\n")
            
        if len(problematic_samples) > 50:
            f.write(f"*Note: Only the first 50 of {len(problematic_samples)} problematic translation samples are listed here. The full list has been saved to [problematic_translation_samples.json](file:///{output_problems_path}).*\n")

    print(f"Generated markdown report at: {report_path}")

if __name__ == "__main__":
    main()
