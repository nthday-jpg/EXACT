from __future__ import annotations

import argparse
from collections import Counter
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
	sys.path.insert(0, str(ROOT_DIR))

from src.physics.registry import get_solver_prompt
from src.physics.router import QuestionClassification


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Process a physics distillation dataset.")
	parser.add_argument("--input", default="runs/physics_distillation_incorrect.json", help="Path to the source distillation JSON")
	parser.add_argument("--output", default="data/processed/physics_distillation.json", help="Path to the processed JSON output")
	parser.add_argument("--reasoning-ratio", type=float, default=0.6, help="Fraction of records that should include reasoning policies in the input field")
	parser.add_argument("--seed", type=int, default=42, help="Random seed for reasoning-prompt sampling")
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


def _domain_list(record: Dict[str, Any]) -> List[str]:
	domains = record.get("domains")
	if not isinstance(domains, list):
		return []
	return [domain for domain in domains if isinstance(domain, str) and domain.strip()]

def _extract_warnings(record: Dict[str, Any]) -> List[str]:
	warnings = record.get("warnings")
	if not isinstance(warnings, list):
		return []
	return [warning for warning in warnings if isinstance(warning, str) and warning.strip()]

def _count_domains(records: List[Dict[str, Any]]) -> Counter[str]:
	counts: Counter[str] = Counter()
	for record in records:
		for domain in set(_domain_list(record)):
			counts[domain] += 1
	return counts


def _build_input_text(
	question: str,
	solver_prompt: str,
) -> str:
	prefix = solver_prompt.strip() if solver_prompt.strip() else "<reasoning_policies></reasoning_policies>"
	parts = [prefix]
	parts.append(f"<question>\n{question}\n</question>")
	return "\n\n".join(parts)


def _build_summary_table(title: str, counts: Counter[str], total: int) -> str:
	lines = [f"## {title}", "", "| Domain | Count |", "| --- | ---: |"]
	for domain, count in sorted(counts.items()):
		lines.append(f"| {domain} | {count} |")
	lines.append(f"| **Total records** | **{total}** |")
	return "\n".join(lines)


def _write_summary_md(
	*,
	output_path: Path,
	source_stats: List[Dict[str, Any]],
	processed_records: List[Dict[str, Any]],
	reasoning_count: int,
	reasoning_ratio: float,
) -> None:
	summary_path = output_path.with_name(f"{output_path.stem}_summary.md")
	lines: List[str] = [
		"# Physics Distillation Summary",
		"",
		f"- Output file: {output_path.name}",
		f"- Reasoning ratio: {reasoning_ratio:.2f}",
		f"- Records with reasoning policies: {reasoning_count} / {len(processed_records)}",
		"",
	]
	lines.append(_build_summary_table("Processed Output", _count_domains(processed_records), len(processed_records)))
	summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
	print(f"Wrote summary to {summary_path}")


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
		record["output"] = record.pop("model_output", "")
		record["answer"] = record.pop("model_answer", None)
		record.pop("is_correct", None)
		record.pop("correct_answer", None)
	return filtered


def main() -> None:
	args = _parse_args()
	input_path = _resolve_path(args.input)
	output_path = _resolve_path(args.output)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	rng = random.Random(args.seed)

	input_paths = _candidate_input_paths(input_path)
	if not input_paths:
		raise FileNotFoundError(str(input_path))
	source_stats: List[Dict[str, Any]] = []
	records: List[Dict[str, Any]] = []
	for candidate_path in input_paths:
		candidate_records = _read_json_list(candidate_path)
		records.extend(candidate_records)
		source_stats.append(
			{
				"title": candidate_path.name,
				"counts": _count_domains(candidate_records),
				"total": len(candidate_records),
			}
		)
	processed = process_dataset(records)
	if processed:
		reasoning_count = min(len(processed), max(0, round(len(processed) * args.reasoning_ratio)))
		sampled_indices = set(rng.sample(range(len(processed)), reasoning_count))
	else:
		reasoning_count = 0
		sampled_indices = set()
	for index, record in enumerate(processed):
		domains = _domain_list(record)
		warnings = _extract_warnings(record)
		solver_prompt = get_solver_prompt(
			QuestionClassification(domains=domains, warnings=warnings)
		)
		question = record.get("question", "")
		record["input"] = _build_input_text(question, solver_prompt)
	output_path.write_text(json.dumps(processed, indent=2, ensure_ascii=False), encoding="utf-8")
	_write_summary_md(
		output_path=output_path,
		source_stats=source_stats,
		processed_records=processed,
		reasoning_count=reasoning_count,
		reasoning_ratio=args.reasoning_ratio,
	)

	print(f"Loaded {len(records)} records from {', '.join(str(path) for path in input_paths)}")
	print(f"Kept {len(processed)} correct unique records")
	print(f"Wrote processed dataset to {output_path}")


if __name__ == "__main__":
	main()