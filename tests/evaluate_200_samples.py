import json
import os
import sys
import time
import random
import argparse
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Disable Z3 proof globally for stability
import z3
z3.set_param('proof', False)

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline


def compare_answers(correct, predicted) -> bool:
    """Compare answers robustly across different formats (strings, lists)."""
    if isinstance(correct, list) and isinstance(predicted, list):
        return sorted([str(x).strip().lower() for x in correct]) == sorted([str(x).strip().lower() for x in predicted])
    if isinstance(correct, list) and isinstance(predicted, str):
        return len(correct) == 1 and str(correct[0]).strip().lower() == predicted.strip().lower()
    if isinstance(correct, str) and isinstance(predicted, list):
        return len(predicted) == 1 and str(predicted[0]).strip().lower() == correct.strip().lower()

    return str(correct).strip().lower() == str(predicted).strip().lower()


def expand_dataset(dataset: list[dict]) -> list[dict]:
    """Expand each JSON sample into one eval item per question.

    Each item has:
        sample_idx   – index of the original JSON sample
        question_idx – index of the question within that sample
        premises_nl  – list of NL premise strings
        question     – single question string
        correct_ans  – corresponding correct answer
    """
    items = []
    for s_idx, sample in enumerate(dataset):
        premises_nl = sample.get("premises-NL", [])
        # Guard: ensure premises_nl is always a list of strings
        if isinstance(premises_nl, str):
            premises_nl = [premises_nl]

        questions = sample.get("questions", [])
        answers = sample.get("answers", [])

        for q_idx, (question, correct_ans) in enumerate(zip(questions, answers)):
            items.append({
                "sample_idx": s_idx,
                "question_idx": q_idx,
                "premises_nl": premises_nl,
                "question": question,
                "correct_ans": correct_ans,
            })
    return items


def evaluate_single_item(eval_idx: int, item: dict, pipeline: LogicalReasoningPipeline) -> dict:
    """Evaluate a single (premises, question) pair with retry mechanism for rate limits."""
    premises_nl = item["premises_nl"]
    question = item["question"]
    correct_ans = item["correct_ans"]
    sample_idx = item["sample_idx"]
    question_idx = item["question_idx"]

    max_retries = 6
    backoff_factor = 2.0

    for attempt in range(max_retries):
        try:
            start_time = time.time()
            result = pipeline.run_pipeline(premises_nl, question)
            elapsed = time.time() - start_time

            predicted_ans = result["answer"]
            is_match = compare_answers(correct_ans, predicted_ans)

            # Extract Z3 result
            z3_res = "unknown"
            if "verification" in result and result["verification"] is not None:
                z3_res = str(result["verification"].get("result", "unknown"))

            return {
                "eval_idx": eval_idx,
                "sample_idx": sample_idx,
                "question_idx": question_idx,
                "success": True,
                "is_match": is_match,
                "correct_ans": correct_ans,
                "predicted_ans": predicted_ans,
                "confidence": result.get("confidence", 0.0),
                "conclusion_fol": result.get("conclusion_fol") or "",
                "z3_result": z3_res,
                "cot": result.get("cot", []),
                "elapsed_sec": elapsed,
            }
        except Exception as e:
            err_msg = str(e)
            if attempt < max_retries - 1 and any(x in err_msg.lower() for x in ["429", "rate limit", "concurrency", "timeout", "connection"]):
                sleep_time = random.uniform(1.5, 3.5) * (backoff_factor ** attempt)
                print(f"[Item {eval_idx} (S{sample_idx}Q{question_idx}) - Attempt {attempt+1}] "
                      f"Rate-limited. Retrying in {sleep_time:.2f}s... Error: {err_msg}")
                time.sleep(sleep_time)
            else:
                return {
                    "eval_idx": eval_idx,
                    "sample_idx": sample_idx,
                    "question_idx": question_idx,
                    "success": False,
                    "error": f"Error after {attempt+1} attempts: {err_msg}",
                }


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Evaluate current logic pipeline. Each (sample, question) pair is one eval item."
    )
    parser.add_argument("--limit", "-l", type=int, default=50,
                        help="Max number of (sample, question) pairs to evaluate (default:  200)")
    parser.add_argument("--endpoint", type=str, default=None,
                        help="Remote endpoint base URL (without /v1). Ignored if --modal-url is set.")
    parser.add_argument("--modal-url", type=str, default="https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run",
                        help="Modal Labs endpoint URL (e.g. https://your-workspace--exact-qwen3-8b-lora-api.modal.run). "
                             "Sets --endpoint and --model-name automatically.")
    parser.add_argument("--model-name", type=str, default=None,
                        help="Model name to pass to the endpoint (default: 'tgi' for HF TGI, "
                             "'exact-qwen3-8b' for Modal)")
    parser.add_argument("--jobs", "-j", type=int, default=4,
                        help="Number of concurrent worker threads (default: 4)")
    parser.add_argument("--local", action="store_true",
                        help="Run evaluation locally on your GPU (loads adapter from results/)")
    parser.add_argument("--device", type=str, default="cuda:0",
                        help="CUDA device to use for local model execution (default: 'cuda:0')")
    args = parser.parse_args()

    # Resolve endpoint & model name
    if args.local:
        args.endpoint = "local"
        args.model_name = "local-exact-qwen3-8b"
        args.jobs = 1  # Force single thread for local GPU execution to prevent OOM
        args.modal_url = None
    elif args.modal_url:
        # Modal URL already includes the full base; /v1 will be appended below
        modal_base = args.modal_url.rstrip("/")
        args.endpoint = modal_base
        if not args.model_name:
            args.model_name = "exact-qwen3-8b"
    elif not args.endpoint:
        raise RuntimeError(
            "No endpoint specified. Use --endpoint <URL>, --modal-url <URL> or --local.\n"
            "Example (Local):  uv run tests/evaluate_200_samples.py --local\n"
            "Example (Modal):  uv run tests/evaluate_200_samples.py "
            "--modal-url https://<workspace>--exact-qwen3-8b-lora-api.modal.run\n"
            "Example (HF):     uv run tests/evaluate_200_samples.py "
            "--endpoint https://<id>.endpoints.huggingface.cloud"
        )
    if not args.model_name:
        args.model_name = "tgi"  # default for HF TGI endpoints

    # 1. Load dataset and expand into flat (sample, question) items
    data_path = root_dir / "data" / "logic_based.json"

    print(f"Loading dataset from: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    all_items = expand_dataset(dataset)
    total_available = len(all_items)
    limit = min(args.limit, total_available)

    print(f"Loaded {len(dataset)} JSON samples → expanded to {total_available} (sample, question) pairs.")
    print(f"Will evaluate the first {limit} pairs.")

    # 2. Initialize LLM client and pipeline
    if args.local:
        endpoint_label = "Local GPU"
        endpoint_url = "localhost"
        base_url = "local"
        model_name = args.model_name
        api_key = "local-placeholder"
    else:
        endpoint_url = args.endpoint.rstrip("/")
        base_url = f"{endpoint_url}/v1"
        model_name = args.model_name

        is_modal = args.modal_url is not None
        endpoint_label = "Modal Labs" if is_modal else "HuggingFace Dedicated Endpoint"

        # Modal does not need a real API key — use a placeholder
        if is_modal:
            api_key = os.getenv("MODAL_API_KEY") or "modal-placeholder"
        else:
            api_key = os.getenv("HF_API_KEY")
            if not api_key:
                raise RuntimeError("HF_API_KEY is not set in environment or .env file.")

    print(f"Using {endpoint_label}: {endpoint_url}")
    print(f"  base_url : {base_url}")
    print(f"  model    : {model_name}")

    if args.local:
        client = LLMClient(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            frequency_penalty=0.0,
            extra_body={},
            use_local=True,
            model_dir=str(root_dir / "results"),
            device=args.device
        )
        pipeline = LogicalReasoningPipeline(use_local=True, llm_client=client, model_dir=str(root_dir / "results"), device=args.device)
    else:
        client = LLMClient(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            frequency_penalty=0.0,
            extra_body={},
            use_local=False,
        )
        pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)
    
    model_info = f"{endpoint_label} ({endpoint_url})"

    print(f"Running with {args.jobs} worker thread(s)...")

    # 3. Run evaluation
    print(f"\nStarting evaluation of {limit} (sample, question) pairs...")
    results = []
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_eval_idx = {
            executor.submit(evaluate_single_item, eval_idx, all_items[eval_idx], pipeline): eval_idx
            for eval_idx in range(limit)
        }

        completed = 0
        for future in concurrent.futures.as_completed(future_to_eval_idx):
            res = future.result()
            results.append(res)
            completed += 1

            if res["success"]:
                match_str = "MATCH 🟢" if res["is_match"] else "MISMATCH 🔴"
                print(
                    f"[{completed}/{limit}] "
                    f"S{res['sample_idx']}Q{res['question_idx']} "
                    f"({res['elapsed_sec']:.2f}s) | {match_str} | Z3: {res['z3_result']}"
                )
            else:
                print(
                    f"[{completed}/{limit}] "
                    f"S{res['sample_idx']}Q{res['question_idx']} FAILED ❌ | Error: {res['error']}"
                )

    total_elapsed = time.time() - start_time

    # 4. Compute metrics
    results.sort(key=lambda x: x["eval_idx"])

    successful_runs = [r for r in results if r["success"]]
    failed_runs = [r for r in results if not r["success"]]

    matches = sum(1 for r in successful_runs if r["is_match"])
    mismatches = sum(1 for r in successful_runs if not r["is_match"])

    accuracy = (matches / len(successful_runs)) * 100 if successful_runs else 0.0
    pass_rate = (len(successful_runs) / limit) * 100

    # Z3 stats
    z3_unsat_count = sum(1 for r in successful_runs if r["z3_result"] == "unsat")
    z3_sat_count = sum(1 for r in successful_runs if r["z3_result"] == "sat")
    z3_unknown_count = sum(1 for r in successful_runs if r["z3_result"] == "unknown")

    # 5. Save results
    output_dir = root_dir / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "evaluation_logic_200.json"

    summary = {
        "evaluation_summary": {
            "model_name": model_info,
            "total_json_samples": len(dataset),
            "total_eval_pairs": total_available,
            "evaluated_pairs": limit,
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "matches_count": matches,
            "mismatches_count": mismatches,
            "accuracy_percent": round(accuracy, 2),
            "pass_rate_percent": round(pass_rate, 2),
            "z3_stats": {
                "unsat (proved contradiction)": z3_unsat_count,
                "sat (proved consistent/not entailed)": z3_sat_count,
                "unknown (Z3 cannot verify)": z3_unknown_count,
            },
            "total_time_sec": round(total_elapsed, 2),
            "avg_time_per_pair_sec": round(total_elapsed / limit, 2) if limit else 0.0,
        },
        "details": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Report saved to: {output_file}")
    print(f"Total Time: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
    print(f"Average Time per Pair: {total_elapsed/limit:.2f} seconds")
    print("-" * 70)
    print(f"JSON Samples in Dataset: {len(dataset)} | Total Q-A Pairs: {total_available}")
    print(f"Evaluated Pairs:  {limit}")
    print(f"Successful Runs:  {len(successful_runs)} ({pass_rate:.1f}%)")
    print(f"Failed Runs:      {len(failed_runs)} ({100 - pass_rate:.1f}%)")
    print(f"Correct Matches:  {matches}")
    print(f"Wrong Mismatches: {mismatches}")
    print(f"Pipeline Entailment Accuracy: {accuracy:.2f}%")
    print("-" * 70)
    print("Z3 SATISFIABILITY STATS:")
    print(f"  - UNSAT (Formally Entailed & Proved): {z3_unsat_count}")
    print(f"  - SAT (Definitively Not Entailed):    {z3_sat_count}")
    print(f"  - UNKNOWN (Undecided/Parse issues):   {z3_unknown_count}")
    print("=" * 70)


if __name__ == "__main__":
    main()
