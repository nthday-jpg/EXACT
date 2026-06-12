from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from tqdm import tqdm

from src.physics.registry import get_solver_prompt
from src.physics.router import QuestionClassification, classify_question
from src.physics.runner import PhysicsRunner
from src.physics.solver import PhysicsSolver
from src.physics.types import PhysicsTask
from src.physics.evaluator import PhysicsEvaluator
from src.utils.physics_tasks import load_physics_tasks

# --- CONFIGURATION ---
HF_BASE_URL = "https://router.huggingface.co/v1"
# Standard OpenAI-compatible endpoint for Google Gemini
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1/openai/"

SOLVER_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507:together"

GEMINI_API_KEYS = [
]

GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite"
]
# Set to True to skip Gemini and use Qwen/HF directly
IGNORE_GEMINI = False 

class ModelManager:
    """Manages global model/key state and handles the switch across all tasks."""
    def __init__(self, attempts: List[Tuple[str, str, str]]):
        # List of (model_name, api_key, base_url)
        self.attempts = attempts
        self.current_index = 0
        self.lock = asyncio.Lock()

    def get_current(self) -> Tuple[str, str, str, int]:
        """Returns (model_name, api_key, base_url, index)"""
        idx = self.current_index
        if idx >= len(self.attempts):
            return None, None, None, idx
        model, key, url = self.attempts[idx]
        return model, key, url, idx

    async def switch_to_next(self, failed_index: int):
        """Globally moves to the next model/key if the error occurred on the current one."""
        async with self.lock:
            if failed_index == self.current_index:
                self.current_index += 1
                if self.current_index < len(self.attempts):
                    new_m, _, _ = self.attempts[self.current_index]
                    print(f"\n[Global Switch] Moving to next model/key: {new_m}")
                else:
                    print("\n[Global Switch] ALL API KEYS AND MODELS EXHAUSTED.")

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a physics distillation dataset.")
    parser.add_argument("--input", dest="input_path", default="runs/physics_distillation.json")
    parser.add_argument("--output", default="runs/physics_distillation.json")
    parser.add_argument("--n-samples", dest="n_sample", type=int, default=-1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--api-key", help="HF API Key")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--concurrency", type=int, default=8)
    return parser.parse_args()

def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute(): return path
    return Path(__file__).resolve().parents[1] / path

def _load_teacher_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "src" / "agents" / "physics_distilation" / "teacher_prompt.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""

def _read_existing_json_records(path: Path) -> List[Dict[str, Any]]:
    if not path.exists(): return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except: return []

def _append_json_records(path: Path, new_records: List[Dict[str, Any]], allow_dupes: bool = False) -> None:
    if not new_records: return
    records = _read_existing_json_records(path)
    records.extend(new_records)
    if not allow_dupes:
        unique = {r.get("question", "").strip(): r for r in records if r.get("question")}
        records = list(unique.values())
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

async def _run_distillation(
    tasks: List[PhysicsTask],
    hf_api_key: str,
    temperature: float,
    concurrency: int,
    paths: Dict[str, Path]
) -> List[Dict[str, Any]]:
    
    # 1. Build Global Attempts List
    attempts = []
    if not IGNORE_GEMINI:
        for key in GEMINI_API_KEYS:
            for model in GEMINI_MODELS:
                # Store (Model, Key, Specific Endpoint)
                attempts.append((model, key, GEMINI_BASE_URL))
    
    # Final fallback to Qwen via HF
    attempts.append((SOLVER_MODEL, hf_api_key, HF_BASE_URL))
    
    manager = ModelManager(attempts)
    semaphore = asyncio.Semaphore(concurrency)
    records: List[Dict[str, Any]] = []
    teacher_prompt = _load_teacher_prompt()

    def save_checkpoint(current_batch: List[Dict[str, Any]]):
        correct = [r for r in current_batch if r.get("is_correct") is True]
        incorrect = [r for r in current_batch if r.get("is_correct") is False]
        _append_json_records(paths["correct"], correct, allow_dupes=True)
        _append_json_records(paths["incorrect"], incorrect, allow_dupes=False)
        print(f"\n[Checkpoint] Saved {len(correct)} correct and {len(incorrect)} incorrect records.")

    async def _run_one(task: PhysicsTask) -> Dict[str, Any]:
        async with semaphore:
            # Stage 1: Classification (Always uses HF)
            domains = task.metadata.get("domains") if task.metadata else None
            if not domains:
                try:
                    classification = await asyncio.to_thread(
                        classify_question, task.question,
                        model_name="meta-llama/Llama-3.1-8B-Instruct:featherless-ai",
                        api_key=hf_api_key, base_url=HF_BASE_URL, temperature=0.0
                    )
                    domains = classification.domains
                except: domains = []

            solver_prompt = get_solver_prompt(QuestionClassification(domains=domains))
            evaluator = PhysicsEvaluator()

            # Stage 2: Solving with Global Switching
            while True:
                model_name, api_key, base_url, current_idx = manager.get_current()
                
                if model_name is None:
                    return {"is_correct": None, "question": task.question, "error": "All providers exhausted", "domains": domains}

                try:
                    solver = PhysicsSolver(
                        model_name=model_name,
                        api_key=api_key,
                        base_url=base_url, # Dynamically switch between Google and HF
                        system_prompt=teacher_prompt,
                        solver_prompt=solver_prompt,
                        temperature=0.4,
                        max_tokens=16384,
                    )
                    
                    runner = PhysicsRunner(solver=solver, evaluator=evaluator)
                    # solver.py raises on system errors (429, 503, quota, etc)
                    evaluation = await asyncio.to_thread(runner.run, [task], verbose=False)
                    eval_obj = evaluation[0]
                    
                    return {
                        "is_correct": getattr(eval_obj, "is_correct", False),
                        "question": task.question,
                        "model_output": eval_obj.result.raw_response,
                        "model_answer": eval_obj.result.model_answer,
                        "correct_answer": getattr(task, "correct", None),
                        "domains": domains,
                        "model_used": model_name
                    }
                except Exception as exc:
                    # Switch global index and retry this task with the next available combo
                    await manager.switch_to_next(current_idx)
                    continue

    pending = [asyncio.create_task(_run_one(task)) for task in tasks]

    try:
        with tqdm(total=len(pending), desc="Distilling") as pbar:
            for coro in asyncio.as_completed(pending):
                res = await coro
                records.append(res)
                pbar.update(1)
                if len(records) >= 50:
                    save_checkpoint(records)
                    records = []
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[interrupt] Stopping tasks...")
    finally:
        if records:
            save_checkpoint(records)

    return records

def main() -> None:
    args = _parse_args()
    load_dotenv()
    hf_key = args.api_key or os.getenv("HF_API_KEY")
    if not hf_key:
        print("Error: Missing HF API key")
        sys.exit(1)

    input_path = _resolve_path(args.input_path)
    output_path = _resolve_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    correct_p = output_path.parent / (output_path.stem + "_correct" + output_path.suffix)
    incorrect_p = output_path.parent / (output_path.stem + "_incorrect" + output_path.suffix)

    existing_q = set()
    for p in [correct_p, incorrect_p]:
        for r in _read_existing_json_records(p):
            if q := r.get("question"): existing_q.add(q.strip())

    all_tasks = load_physics_tasks(str(input_path), num_samples=args.n_sample, seed=args.seed)
    tasks = [t for t in all_tasks if t.question.strip() not in existing_q]
    
    if not tasks:
        print("All tasks processed.")
        return

    print(f"Total tasks: {len(tasks)}")
    if not IGNORE_GEMINI:
        print(f"Priority: Google Gemini ({len(GEMINI_API_KEYS)} keys)")
    print(f"Final Fallback: HuggingFace ({SOLVER_MODEL})")

    asyncio.run(_run_distillation(
        tasks=tasks, hf_api_key=hf_key,
        temperature=args.temperature, concurrency=args.concurrency,
        paths={"correct": correct_p, "incorrect": incorrect_p}
    ))
    
if __name__ == "__main__":
    main()