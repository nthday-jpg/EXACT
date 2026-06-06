import json
import os
import sys
import time
import random
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Disable Z3 proof globally for stability
import z3
z3.set_param('proof', False)

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline

def normalize_ans(ans):
    if isinstance(ans, list):
        return sorted([normalize_ans(x) for x in ans])
    ans_str = str(ans).strip().lower()
    if ans_str in ("yes", "true"):
        return "yes"
    if ans_str in ("no", "false"):
        return "no"
    if ans_str in ("uncertain", "unknown"):
        return "uncertain"
    return ans_str

def compare_answers(correct, predicted) -> bool:
    return normalize_ans(correct) == normalize_ans(predicted)

def main():
    load_dotenv()
    
    # 1. Load dataset
    data_path = root_dir / "data" / "processed" / "logic_merged_valid.json"
    print(f"Loading validation dataset from: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    print(f"Loaded {len(dataset)} examples.")
    
    # Shuffle with a fixed seed for reproducibility and pick 5 samples
    random.seed(42)
    selected_indices = random.sample(range(len(dataset)), min(5, len(dataset)))
    selected_samples = [dataset[idx] for idx in selected_indices]
    
    print(f"Selected {len(selected_samples)} representative samples for evaluation.")
    
    # 2. Initialize client and pipeline
    print("Initializing LLM client Qwen/Qwen3-8B:featherless-ai...")
    client = LLMClient(
        model_name="Qwen/Qwen3-8B:featherless-ai",
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ.get("HF_API_KEY"),
        temperature=0.1
    )
    client.tokenizer = None  # Force chat completions to avoid completions choices message bug
    
    pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)

    # Patch to force is_finetuned to True for translation & pipeline checks (speed up)
    old_translate_list = pipeline.translation_pipeline.translate_list
    def patched_translate_list(nl_list, max_new_tokens=None):
        orig_name = pipeline.llm_client.model_name
        pipeline.llm_client.model_name = "exact-qwen-lora"
        old_generate = pipeline.llm_client.generate
        def patched_generate(prompt, max_tokens=None, system_prompt=None):
            pipeline.llm_client.model_name = orig_name
            try:
                return old_generate(prompt, max_tokens, system_prompt)
            finally:
                pipeline.llm_client.model_name = "exact-qwen-lora"
        pipeline.llm_client.generate = patched_generate
        try:
            return old_translate_list(nl_list, max_new_tokens)
        finally:
            pipeline.llm_client.model_name = orig_name
            pipeline.llm_client.generate = old_generate

    pipeline.translation_pipeline.translate_list = patched_translate_list

    old_run_pipeline = pipeline.run_pipeline
    def patched_run_pipeline(premises_nl, conclusion_nl, question_type=None):
        orig_name = pipeline.llm_client.model_name
        pipeline.llm_client.model_name = "exact-qwen-lora"
        old_generate = pipeline.llm_client.generate
        def patched_generate(prompt, max_tokens=None, system_prompt=None):
            pipeline.llm_client.model_name = orig_name
            try:
                return old_generate(prompt, max_tokens, system_prompt)
            finally:
                pipeline.llm_client.model_name = "exact-qwen-lora"
        pipeline.llm_client.generate = patched_generate
        try:
            return old_run_pipeline(premises_nl, conclusion_nl, question_type)
        finally:
            pipeline.llm_client.model_name = orig_name
            pipeline.llm_client.generate = old_generate

    pipeline.run_pipeline = patched_run_pipeline
    
    # 3. Run evaluation
    results = []
    matches = 0
    mismatches = 0
    start_time = time.time()

    
    for i, sample in enumerate(selected_samples):
        orig_idx = selected_indices[i]
        premises_nl = sample["premises-NL"]
        question = sample["question"]
        correct_ans = sample["answer"]
        dataset_source = sample.get("dataset_source", "unknown")
        story_id = sample.get("story_id", "unknown")
        
        print(f"\n--- [{i+1}/{len(selected_samples)}] Sample {orig_idx} (Source: {dataset_source}, Story: {story_id}) ---")
        print(f"Premises: {premises_nl}")
        print(f"Question: {question}")
        print(f"Correct Answer: {correct_ans}")
        
        item_start = time.time()
        try:
            res = pipeline.run_pipeline(premises_nl, question)
            elapsed = time.time() - item_start
            
            predicted_ans = res["answer"]
            is_match = compare_answers(correct_ans, predicted_ans)
            
            if is_match:
                matches += 1
                match_str = "MATCH 🟢"
            else:
                mismatches += 1
                match_str = "MISMATCH 🔴"
                
            z3_res = "unknown"
            if "verification" in res and res["verification"] is not None:
                z3_res = str(res["verification"].get("result", "unknown"))
                
            print(f"Predicted Answer: {predicted_ans} | {match_str} | Z3: {z3_res} ({elapsed:.2f}s)")
            
            results.append({
                "sample_idx": orig_idx,
                "dataset_source": dataset_source,
                "story_id": story_id,
                "premises_nl": premises_nl,
                "premises_fol": res.get("premises_fol", []),
                "conclusion_fol": res.get("conclusion_fol", ""),
                "question": question,
                "correct_ans": correct_ans,
                "predicted_ans": predicted_ans,
                "is_match": is_match,
                "z3_result": z3_res,
                "confidence": res.get("confidence", 0.0),
                "reasoning": res.get("reasoning", ""),
                "cot": res.get("cot", []),
                "elapsed_sec": elapsed,
                "success": True
            })
            
        except Exception as e:
            elapsed = time.time() - item_start
            print(f"Failed to process sample {orig_idx}: {e}")
            results.append({
                "sample_idx": orig_idx,
                "dataset_source": dataset_source,
                "story_id": story_id,
                "premises_nl": premises_nl,
                "question": question,
                "correct_ans": correct_ans,
                "success": False,
                "error": str(e),
                "elapsed_sec": elapsed
            })
            
    total_elapsed = time.time() - start_time
    
    # 4. Save results
    output_dir = root_dir / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "qwen3_validation_results.json"
    
    successful_runs = [r for r in results if r["success"]]
    accuracy = (matches / len(successful_runs)) * 100 if successful_runs else 0.0
    
    z3_unsat = sum(1 for r in successful_runs if r["z3_result"] == "unsat")
    z3_sat = sum(1 for r in successful_runs if r["z3_result"] == "sat")
    z3_unknown = sum(1 for r in successful_runs if r["z3_result"] == "unknown")
    
    summary = {
        "summary": {
            "model_name": "Qwen/Qwen3-8B:featherless-ai",
            "evaluated_samples": len(results),
            "successful_runs": len(successful_runs),
            "failed_runs": len(results) - len(successful_runs),
            "matches": matches,
            "mismatches": mismatches,
            "accuracy": round(accuracy, 2),
            "z3_stats": {
                "unsat": z3_unsat,
                "sat": z3_sat,
                "unknown": z3_unknown
            },
            "total_time_sec": round(total_elapsed, 2)
        },
        "details": results
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Accuracy: {accuracy:.2f}% ({matches}/{len(successful_runs)})")
    print(f"Z3 unsat (proved): {z3_unsat} | sat (consistent): {z3_sat} | unknown: {z3_unknown}")
    print(f"Results saved to: {output_file}")
    print(f"Total Time: {total_elapsed:.2f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()
