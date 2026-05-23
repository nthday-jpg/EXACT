import json
import os
import re
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports of src
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from dotenv import load_dotenv
from openai import OpenAI

from src.utils.normalization import normalize_logic_fol_entry, normalize_logic_premise_text

PREDICATE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\(")
EXCLUDED_SYMBOLS = {"ForAll", "Exists"}


def build_client() -> OpenAI:
	api_key = os.environ.get("GEMINI_API_KEY")
	if not api_key:
		raise EnvironmentError("GEMINI_API_KEY is not set")
	return OpenAI(
		api_key=api_key,
		base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
	)


def load_prompt(prompt_path: Path) -> str:
	content = prompt_path.read_text(encoding="utf-8").strip()
	if not content:
		raise ValueError(f"Prompt file is empty: {prompt_path}")
	return content


def extract_predicates(fol: str) -> list[str]:
	return [name for name in PREDICATE_RE.findall(fol) if name not in EXCLUDED_SYMBOLS]


def has_only_single_char_predicates(premises: list[str]) -> bool:
	if not premises:
		return False
	for fol in premises:
		predicates = extract_predicates(fol)
		if not predicates:
			return False
		if any(len(name) != 1 for name in predicates):
			return False
	return True


def normalize_samples(data: list[dict]) -> list[dict]:
	processed = []
	for sample in data:
		new_sample = dict(sample)
		premises = sample.get("premises-NL")
		if premises is not None:
			if not isinstance(premises, list):
				raise TypeError("premises-NL must be a list")
			new_sample["premises-NL"] = [normalize_logic_premise_text(p) for p in premises]

		fol_list = sample.get("premises-FOL")
		if fol_list is not None:
			if not isinstance(fol_list, list):
				raise TypeError("premises-FOL must be a list")
			new_sample["premises-FOL"] = [normalize_logic_fol_entry(p) for p in fol_list]
		processed.append(new_sample)
	return processed


def filter_single_char_samples(data: list[dict]) -> list[tuple[int, dict]]:
	filtered = []
	for index, sample in enumerate(data):
		premises = sample.get("premises-FOL")
		if isinstance(premises, list) and has_only_single_char_predicates(premises):
			filtered.append((index, sample))
	return filtered


def extract_payload(sample: dict) -> dict:
	return {
		"premises-FOL": sample.get("premises-FOL", []),
		"premises-NL": sample.get("premises-NL", []),
	}


def rewrite_sample(sample: dict, cleaned: dict) -> dict:
	updated = dict(sample)
	updated["premises-FOL"] = cleaned.get("premises-FOL", sample.get("premises-FOL", []))
	return updated


def standardize_samples(
	data: list[tuple[int, dict]],
	prompt: str,
	client: OpenAI,
	max_samples: int,
) -> list[tuple[int, dict]]:
	if max_samples != -1 and max_samples < 0:
		raise ValueError("max_samples must be -1 or a non-negative integer")

	import time

	processed = []
	limit = len(data) if max_samples == -1 else min(max_samples, len(data))
	for position, (index, sample) in enumerate(data[:limit]):
		print(f"Processing sample {position + 1}/{limit}")
		payload = extract_payload(sample)
		response = client.chat.completions.create(
			model="gemini-3.1-flash-lite-preview",
			response_format={"type": "json_object"},
			messages=[
				{"role": "system", "content": prompt},
				{"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
			],
		)
		content = response.choices[0].message.content or "{}"
		try:
			cleaned = json.loads(content)
		except json.JSONDecodeError as exc:
			raise ValueError(f"Invalid JSON response at index {index}: {content}") from exc

		processed.append((index, rewrite_sample(sample, cleaned)))
		if position < limit - 1:
			time.sleep(4.5)
	return processed


def run_pipeline(input_path: Path, output_path: Path, prompt_path: Path, max_samples: int) -> None:
	data = json.loads(input_path.read_text(encoding="utf-8"))
	if not isinstance(data, list):
		raise TypeError("Expected a list in logic_based.json")

	missing_fol = sum(1 for sample in data if not sample.get("premises-FOL"))
	print(f"Missing premises-FOL: {missing_fol}")

	normalized = normalize_samples(data)
	filtered = filter_single_char_samples(normalized)

	prompt = load_prompt(prompt_path)
	client = build_client()
	standardized = standardize_samples(filtered, prompt, client, max_samples)
	for index, sample in standardized:
		normalized[index] = sample

	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(
		json.dumps(normalized, ensure_ascii=False, indent=2),
		encoding="utf-8",
	)
	print(f"Final output items: {len(normalized)}")

	if normalized:
		first_fol = normalized[0].get("premises-FOL", [])
		if first_fol:
			print(f"First premises-FOL sample: {first_fol[:3]}")
		unique_chars = set("".join("".join(s.get("premises-FOL", [])) for s in normalized))
		print(f"Unique chars in premises-FOL: {sorted(unique_chars)}")


if __name__ == "__main__":
	root = Path(__file__).resolve().parents[1]
	load_dotenv()
	input_path = root / "data" / "logic_based.json"
	output_path = root / "data" / "processed" / "logic_based.json"
	prompt_path = root / "data" / "standardize_prompt.md"
	max_samples = -1
	run_pipeline(input_path, output_path, prompt_path, max_samples)
	print(output_path.as_posix())
