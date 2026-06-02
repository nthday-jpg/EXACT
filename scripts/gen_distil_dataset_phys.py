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


class DistillationError(RuntimeError):
	def __init__(self, message: str, records: List[Dict[str, Any]]):
		super().__init__(message)
		self.records = records


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Create a physics distillation dataset.")
	parser.add_argument("--input", "--csv", dest="input_path", default="data/processed/physics.csv", help="Path to the source physics input file (CSV, JSON, or JSONL)")
	parser.add_argument("--output", default="runs/physics_distillation.json", help="Path to the output JSON")
	parser.add_argument("--n-samples", "--n_samples", dest="n_sample", type=int, default=-1, help="Number of samples to process (-1 for all)")
	parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
	parser.add_argument("--model", default=None, help="Override solver model name")
	parser.add_argument("--router-model", default=None, help="Override router model name")
	parser.add_argument("--api-key", default=None, help="Override API key")
	parser.add_argument("--temperature", type=float, default=0.1, help="Solver temperature")
	parser.add_argument("--concurrency", type=int, default=4, help="Number of concurrent tasks")
	return parser.parse_args()


def _resolve_path(path_str: str) -> Path:
	path = Path(path_str)
	if path.is_absolute():
		return path
	return Path(__file__).resolve().parents[1] / path


def _load_text(path: Path) -> str:
	if path.exists():
		return path.read_text(encoding="utf-8")
	return ""


def _load_teacher_prompt() -> str:
	return _load_text(Path(__file__).resolve().parents[1] / "src" / "agents" / "physics_distilation" / "teacher_prompt.md")


def _load_teacher_fewshot() -> str:
	return _load_text(Path(__file__).resolve().parents[1] / "src" / "agents" / "physics_distilation" / "fewshot.md")


def _read_existing_json_records(path: Path) -> List[Dict[str, Any]]:
	if not path.exists():
		return []
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
	except json.JSONDecodeError:
		return []
	if isinstance(data, list):
		return data
	return []


def _question_key(record: Dict[str, Any]) -> str:
	question = record.get("question")
	return question.strip() if isinstance(question, str) else ""


def _append_json_records(path: Path, new_records: List[Dict[str, Any]]) -> None:
	records = _read_existing_json_records(path)
	records.extend(new_records)
	unique_records: List[Dict[str, Any]] = []
	seen_questions = set()
	for record in reversed(records):
		key = _question_key(record)
		if key and key in seen_questions:
			continue
		if key:
			seen_questions.add(key)
		unique_records.append(record)
	records = list(reversed(unique_records))
	path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_json_records_allow_duplicates(path: Path, new_records: List[Dict[str, Any]]) -> None:
	records = _read_existing_json_records(path)
	records.extend(new_records)
	path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


async def _run_distillation(
	*,
	tasks: List[PhysicsTask],
	model_name: str,
	api_key: Optional[str],
	base_url: str,
	router_model_name: Optional[str],
	router_api_key: str,
	temperature: float,
	concurrency: int,
) -> List[Dict[str, Any]]:
	semaphore = asyncio.Semaphore(max(1, concurrency))
	records: List[Dict[str, Any]] = []
	teacher_prompt = _load_teacher_prompt()
	teacher_fewshot = _load_teacher_fewshot()

	async def _run_one(task: PhysicsTask) -> Dict[str, Any]:
		# Keep everything indented inside the semaphore block
		async with semaphore:
			classification = QuestionClassification(["electrostatics", "geometry"], "Numerical")
			router_model = router_model_name or model_name
			classifier_key = api_key or ""
			classification = await asyncio.to_thread(
				classify_question,
				task.question,
				model_name=router_model,
				api_key=router_api_key or classifier_key,
				temperature=0.0,
			)
			solver_prompt = get_solver_prompt(classification)
			if teacher_fewshot:
				fewshot_block = f"<fewshots>\n{teacher_fewshot}\n</fewshots>"
				solver_prompt = f"{solver_prompt}\n\n{fewshot_block}" if solver_prompt else fewshot_block
			solver = PhysicsSolver(
				model_name=model_name,
				api_key=api_key,
				base_url=base_url,
				system_prompt=teacher_prompt,
				solver_prompt=solver_prompt,
				temperature=temperature,
				max_tokens=4096,
			)
			evaluator = PhysicsEvaluator()
			runner = PhysicsRunner(solver=solver,
						  	evaluator=evaluator
						  	)
			evaluation = await asyncio.to_thread(runner.run, [task], verbose=False)

			try:
				eval_obj = evaluation[0]
				result = eval_obj.result
				is_correct = getattr(eval_obj, "is_correct", None)
				if result.error:
					# Error from the model -> incorrect; include answers when available
					return {
						"is_correct": False,
						"question": task.question,
						"model_output": result.raw_response,
						"model_answer": result.model_answer,
						"correct_answer": getattr(result.task, "correct", None),
						"domains": classification.domains,
					}
				# Normal result: include model and correct answers; evaluator `is_correct` may indicate correctness
				return {
					"is_correct": is_correct,
					"question": result.task.question,
					"model_output": result.raw_response,
					"model_answer": result.model_answer,
					"correct_answer": getattr(result.task, "correct", None),
					"domains": classification.domains,
				}
			except Exception as exc:
				# Any unexpected failure for this task becomes an error record
				return {
					"is_correct": None,
					"question": task.question,
					"model_output": "",
					"model_answer": None,
					"correct_answer": None,
					"domains": getattr(classification, "domains", []),
				}

	pending = [asyncio.create_task(_run_one(task)) for task in tasks]
	for coro in tqdm(asyncio.as_completed(pending), total=len(pending), desc="Distilling"):
		try:
			records.append(await coro)
		except KeyboardInterrupt as exc:
			# User interruption: cancel remaining tasks and return partial results
			for pending_task in pending:
				if not pending_task.done():
					pending_task.cancel()
			await asyncio.gather(*pending, return_exceptions=True)
			raise DistillationError("Interrupted by user", records) from exc
		except asyncio.CancelledError as exc:
			# Task cancellation (often from Ctrl-C) — treat like user interrupt
			for pending_task in pending:
				if not pending_task.done():
					pending_task.cancel()
			await asyncio.gather(*pending, return_exceptions=True)
			raise DistillationError("Interrupted (cancelled)", records) from exc
		except Exception as exc:
			# Cancel remaining tasks and collect completed results
			for pending_task in pending:
				if not pending_task.done():
					pending_task.cancel()
			await asyncio.gather(*pending, return_exceptions=True)
			# Raise a DistillationError carrying partial records
			raise DistillationError(str(exc), records) from exc

	return records


def main() -> None:
	args = _parse_args()
	load_dotenv()

	api_key = args.api_key or os.getenv("HF_API_KEY")
	if not api_key:
		print("[physics-distill] HF_API_KEY not set and no --api-key provided.", file=sys.stderr)
	base_url = "https://router.huggingface.co/v1"
	model_name = "openai/gpt-oss-120b:groq"
	router_model_name = "Qwen/Qwen3-8B:featherless-ai"
	router_api_key = os.getenv("HF_API_KEY") or ""
	if not router_api_key:
		print("[physics-distill] Router HF_API_KEY not set; router calls may fail.", file=sys.stderr)

	input_path = _resolve_path(args.input_path)
	output_path = _resolve_path(args.output)
	output_path.parent.mkdir(parents=True, exist_ok=True)

	tasks = load_physics_tasks(str(input_path), num_samples=args.n_sample, seed=args.seed)
	try:
		records = asyncio.run(
			_run_distillation(
				tasks=tasks,
				model_name=model_name,
				api_key=api_key,
				router_model_name=router_model_name,
				base_url=base_url,
				router_api_key=router_api_key,
				temperature=args.temperature,
				concurrency=args.concurrency,
			)
		)
	except DistillationError as e:
		# Append partial records into the split outputs and report the error.
		correct = [r for r in e.records if r.get("is_correct") is not False]
		incorrect = [r for r in e.records if r.get("is_correct") is False]
		correct_path = output_path.parent / (output_path.stem + "_correct" + output_path.suffix)
		incorrect_path = output_path.parent / (output_path.stem + "_incorrect" + output_path.suffix)
		_append_json_records(correct_path, correct)
		_append_json_records_allow_duplicates(incorrect_path, incorrect)
		print(f"Appended {len(correct)} correct and {len(incorrect)} incorrect partial records to {correct_path} and {incorrect_path} before failure")
		print("Error:", str(e))
		raise SystemExit(1)

	# Append new records into the split correct / incorrect JSON files.
	correct = [r for r in records if r.get("is_correct") is not False]
	incorrect = [r for r in records if r.get("is_correct") is False]
	correct_path = output_path.parent / (output_path.stem + "_correct" + output_path.suffix)
	incorrect_path = output_path.parent / (output_path.stem + "_incorrect" + output_path.suffix)
	_append_json_records(correct_path, correct)
	_append_json_records_allow_duplicates(incorrect_path, incorrect)
	print(f"Appended {len(correct)} correct records to {correct_path}")
	print(f"Appended {len(incorrect)} incorrect records to {incorrect_path}")


if __name__ == "__main__":
	main()
