from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Process a physics distillation dataset.")
	parser.add_argument("--input", default="runs/physics_distillation_incorrect.json", help="Path to the source distillation JSON")
	parser.add_argument("--output", default="data/processed/physics_distillation.json", help="Path to the processed JSON output")
	return parser.parse_args()


def _resolve_path(path_str: str) -> Path:
	path = Path(path_str)
	if path.is_absolute():
		return path
	return Path(__file__).resolve().parents[1] / path


def _candidate_input_paths(path: Path) -> List[Path]:
	candidates: List[Path] = []
	incorrect_path = path.parent / f"{path.stem.replace('_correct', '').replace('_incorrect', '')}_incorrect{path.suffix}"
	correct_path = path.parent / f"{path.stem.replace('_correct', '').replace('_incorrect', '')}_correct{path.suffix}"
	for candidate in [incorrect_path, correct_path]:
		if candidate.exists() and candidate not in candidates:
			candidates.append(candidate)
	if not candidates and path.exists():
		candidates.append(path)
	elif path.exists() and path not in candidates:
		candidates.append(path)
	return candidates


def _read_json_list(path: Path) -> List[Dict[str, Any]]:
	data = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(data, list):
		raise ValueError(f"Expected a JSON list in {path}")
	items: List[Dict[str, Any]] = []
	for index, item in enumerate(data):
		if not isinstance(item, dict):
			raise ValueError(f"Expected object items in {path} at index {index}")
		items.append(item)
	return items


def _question_key(record: Dict[str, Any]) -> str:
	question = record.get("question")
	if not isinstance(question, str):
		return ""
	return " ".join(question.split())


def _dedupe_keep_last(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	unique_records: List[Dict[str, Any]] = []
	seen_questions = set()
	for record in reversed(records):
		key = _question_key(record)
		if key and key in seen_questions:
			continue
		if key:
			seen_questions.add(key)
		unique_records.append(record)
	return list(reversed(unique_records))


def _clean_python_code(code: str) -> str:
	code = code.rstrip()
	if code.endswith(";"):
		code = code[:-1].rstrip()
	code = re.sub(r"\[\s*\\?[\"\'](.*?)\\?[\"\']\s*\]", r"['\1']", code)
	code = code.replace('\\"', '"').replace("\\'", "'")
	return code


def _normalize_correct_answer(record: Dict[str, Any]) -> None:
	correct = record.get("correct_answer")
	if not isinstance(correct, dict):
		return
	inner = correct.get("ans")
	if isinstance(inner, dict):
		flat_answer = inner.get("ans", inner.get("value"))
		flat_unit = inner.get("unit", correct.get("unit"))
		record["correct_answer"] = {"ans": flat_answer, "unit": flat_unit}
	elif "unit" not in correct:
		record["correct_answer"] = {"ans": inner, "unit": correct.get("unit")}


def _normalize_model_output(record: Dict[str, Any]) -> None:
	model_output = record.get("model_output")
	if not isinstance(model_output, str):
		return
	try:
		inner = json.loads(model_output)
	except json.JSONDecodeError:
		return
	if not isinstance(inner, dict):
		return
	python_code = inner.get("python_code")
	if isinstance(python_code, str):
		inner["python_code"] = _clean_python_code(python_code)
	record["model_output"] = json.dumps(inner, ensure_ascii=False)


def _keep_correct_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	kept: List[Dict[str, Any]] = []
	for record in records:
		if record.get("is_correct") is True:
			kept.append(record)
	return kept


def process_dataset(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	filtered = _keep_correct_records(records)
	filtered = _dedupe_keep_last(filtered)
	for record in filtered:
		_normalize_correct_answer(record)
		_normalize_model_output(record)
		record.pop("is_correct", None)
		record.pop("correct_answer", None)
	return filtered


def main() -> None:
	args = _parse_args()
	input_path = _resolve_path(args.input)
	output_path = _resolve_path(args.output)
	output_path.parent.mkdir(parents=True, exist_ok=True)

	input_paths = _candidate_input_paths(input_path)
	if not input_paths:
		raise FileNotFoundError(str(input_path))
	records: List[Dict[str, Any]] = []
	for candidate_path in input_paths:
		records.extend(_read_json_list(candidate_path))
	processed = process_dataset(records)
	output_path.write_text(json.dumps(processed, indent=2, ensure_ascii=False), encoding="utf-8")

	print(f"Loaded {len(records)} records from {', '.join(str(path) for path in input_paths)}")
	print(f"Kept {len(processed)} correct unique records")
	print(f"Wrote processed dataset to {output_path}")


if __name__ == "__main__":
	main()