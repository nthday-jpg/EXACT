
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from tqdm import tqdm

from src.physics.registry import get_solver_prompt
from src.physics.router import QuestionClassification, classify_question
from src.physics.runner import PhysicsRunner
from src.physics.solver import PhysicsSolver
from src.physics.types import PhysicsTask
from src.physics.evaluator import PhysicsEvaluator
from src.utils.physics_tasks import load_physics_tasks

# Constants for the different providers
ROUTER_BASE_URL = "https://router.huggingface.co/v1"
SOLVER_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

class DistillationError(RuntimeError):
	def __init__(self, message: str, records: List[Dict[str, Any]]):
		super().__init__(message)
		self.records = records

class SessionState:
	"""Tracks the current model and key index globally across all tasks."""
	def __init__(self, models: List[str], keys: List[str]):
		self.models = models
		self.keys = keys
		self.model_idx = 0
		self.key_idx = 0
		self.lock = asyncio.Lock()
		self.exhausted = False

	async def get_current(self):
		async with self.lock:
			if self.key_idx >= len(self.keys):
				self.exhausted = True
				return None, None
			return self.models[self.model_idx], self.keys[self.key_idx]

	async def switch_to_next(self, failed_model: str, failed_key: str):
		"""Switches to the next model, or next key if models are exhausted."""
		async with self.lock:
			# Check if another task already switched us while we were waiting for the lock
			if self.models[self.model_idx] != failed_model or self.keys[self.key_idx] != failed_key:
				return 

			print(f"\n[fallback] System error on {failed_model}. Switching...")
			if self.model_idx + 1 < len(self.models):
				self.model_idx += 1
			else:
				self.model_idx = 0
				self.key_idx += 1
			
			if self.key_idx >= len(self.keys):
				self.exhausted = True
				print("[fallback] All models and API keys exhausted.")

def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Create a physics distillation dataset.")
	parser.add_argument("--input", dest="input_path", default="data/processed/physics.csv")
	parser.add_argument("--output", default="runs/physics_distillation.json")
	parser.add_argument("--n-samples", dest="n_sample", type=int, default=-1)
	parser.add_argument("--seed", type=int, default=42)
	parser.add_argument("--models", nargs="+", help="List of Gemini models (e.g. gemini-1.5-pro)")
	parser.add_argument("--api-keys", nargs="+", help="List of Gemini API keys")
	parser.add_argument("--router-api-key", help="HF API key for the router")
	parser.add_argument("--temperature", type=float, default=0.1)
	parser.add_argument("--concurrency", type=int, default=4)
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
	records = _read_existing_json_records(path)
	records.extend(new_records)
	if not allow_dupes:
		unique = {}
		for r in records:
			q = r.get("question", "").strip()
			if q: unique[q] = r
		records = list(unique.values())
	path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

async def _run_distillation(
	tasks: List[PhysicsTask],
	state: SessionState,
	router_api_key: str,
	temperature: float,
	concurrency: int,
) -> List[Dict[str, Any]]:
	semaphore = asyncio.Semaphore(concurrency)
	records: List[Dict[str, Any]] = []
	teacher_prompt = _load_teacher_prompt()

	async def _run_one(task: PhysicsTask) -> Dict[str, Any]:
		async with semaphore:
			while not state.exhausted:
				current_model, current_key = await state.get_current()
				if not current_model: break

				try:
					# 1. Classification (Always HF)
					classification = await asyncio.to_thread(
						classify_question,
						task.question,
						model_name="meta-llama/Llama-3.1-8B-Instruct:featherless-ai",
						api_key=router_api_key,
						base_url=ROUTER_BASE_URL,
						temperature=0.0,
					)
					
					# 2. Solving (Always Gemini)6
					solver = PhysicsSolver(
						model_name=current_model,
						api_key=current_key,
						base_url=SOLVER_BASE_URL,
						system_prompt=teacher_prompt,
						solver_prompt=get_solver_prompt(classification),
						temperature=temperature,
						max_tokens=20000,
					)
					
					runner = PhysicsRunner(solver=solver, evaluator=PhysicsEvaluator())
					evaluation = await asyncio.to_thread(runner.run, [task], verbose=False)
					eval_obj = evaluation[0]
					
					return {
						"is_correct": getattr(eval_obj, "is_correct", False),
						"question": task.question,
						"model_output": eval_obj.result.raw_response,
						"model_answer": eval_obj.result.model_answer,
						"correct_answer": getattr(task, "correct", None),
						"domains": classification.domains,
						"model_used": current_model
					}

				except Exception as exc:
					err_msg = str(exc).lower()
					print(f"\n[error] Model {current_model} with key {current_key} failed: {err_msg}")
					# Check for system errors (Quota, Rate Limit, Overloaded)
					is_system_error = any(x in err_msg for x in ["429", "quota", "limit", "overloaded", "403","404"])
					
					if is_system_error:
						await state.switch_to_next(current_model, current_key)
						continue # Retry this task with the new model/key
					else:
						# Fatal logic error or unexpected exception
						return {
							"is_correct": None,
							"question": task.question,
							"error": str(exc),
							"domains": []
						}
			
			return {"is_correct": None, "question": task.question, "error": "All resources exhausted"}

	pending = [asyncio.create_task(_run_one(task)) for task in tasks]
	for coro in tqdm(asyncio.as_completed(pending), total=len(pending), desc="Distilling"):
		try:
			records.append(await coro)
		except Exception as exc:
			for p in pending: 
				if not p.done(): p.cancel()
			raise DistillationError(str(exc), records)

	return records

def main() -> None:
	args = _parse_args()
	load_dotenv()

	# API Keys and Models for Solver (Gemini)
	gemini_keys = [
		"AQ.Ab8RN6JKWxNxxPX77F_nTgff1x9AOevW9sKDB0S8ztC-JLdj0Q",
		"AQ.Ab8RN6J7zaxvaPU6AgQE6tohF1y93ZDk-oRUBZ7th9xFBaeChQ",
		"AQ.Ab8RN6Ic74WmovZu-rOT1CE02mCY_Fbxot_Eh5LfNbzrfZEWmQ"
]

	gemini_models = [
		"gemini-2.5-flash",
		"gemini-3.5-flash",
		"gemini-3.1-flash-lite",
		"gemini-2.5-flash-lite",
		"gemini-3-flash",
	]
	
	# Router API Key (HF)
	router_key = args.router_api_key or os.getenv("HF_API_KEY")

	if not all([gemini_keys[0], router_key]):
		print("Error: Missing GEMINI_API_KEY or HF_API_KEY")
		sys.exit(1)

	state = SessionState(models=gemini_models, keys=gemini_keys)
	
	input_path = _resolve_path(args.input_path)
	output_path = _resolve_path(args.output)
	output_path.parent.mkdir(parents=True, exist_ok=True)

	tasks = load_physics_tasks(str(input_path), num_samples=args.n_sample, seed=args.seed)
	
	correct_path = output_path.parent / (output_path.stem + "_correct" + output_path.suffix)
	incorrect_path = output_path.parent / (output_path.stem + "_incorrect" + output_path.suffix)

	try:
		records = asyncio.run(_run_distillation(
			tasks=tasks, state=state, router_api_key=router_key,
			temperature=args.temperature, concurrency=args.concurrency
		))
	except DistillationError as e:
		records = e.records

	correct = [r for r in records if r.get("is_correct") is True]
	incorrect = [r for r in records if r.get("is_correct") is False]
	
	_append_json_records(correct_path, correct, allow_dupes=True)
	_append_json_records(incorrect_path, incorrect, allow_dupes=False)
	
	print(f"Done. Correct: {len(correct)}, Incorrect: {len(incorrect)}")

if __name__ == "__main__":
	main()