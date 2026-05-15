import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

from z3 import DeclareSort, Solver

from llm.llm_client import LLMClient
from src.logic.Z3_parser import FolParser, Z3Symbols


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "processed" / "logic_based.json"
INSTRUCTIONS_DIR = ROOT_DIR / "src" / "llm" / "instructions"
PROMPTS_DIR = ROOT_DIR / "src" / "llm" / "prompts"


def load_text(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def render_template(template: str, **kwargs: str) -> str:
	result = template
	for key, value in kwargs.items():
		result = result.replace("{{" + key + "}}", value)
	return result


def parse_json(content: str) -> Any:
	content = content.strip()
	try:
		return json.loads(content)
	except json.JSONDecodeError:
		start = content.find("{")
		end = content.rfind("}")
		if start != -1 and end != -1 and end > start:
			return json.loads(content[start : end + 1])
		raise


def ensure_str_list(value: Any, label: str) -> List[str]:
	if value is None:
		return []
	if not isinstance(value, list):
		raise TypeError(f"{label} must be a list")
	if not all(isinstance(item, str) for item in value):
		raise TypeError(f"{label} must be a list of strings")
	return value


def run_pipeline(
	sample: Dict[str, Any],
	ontology_builder: LLMClient,
	logic_compiler: LLMClient,
	ontology_prompt_template: str,
	logic_prompt_template: str,
) -> Dict[str, Any]:
	result: Dict[str, Any] = {}
	try:
		premises = sample.get("premises-NL", [])
		if not isinstance(premises, list):
			raise TypeError("premises-NL must be a list")
		premises_text = "\n".join(premises)

		ontology_prompt = render_template(
			ontology_prompt_template,
			premises=premises_text,
		)
		ontology_raw = ontology_builder.generate(ontology_prompt)
		ontology = parse_json(ontology_raw)

		ontology_json = json.dumps(ontology, ensure_ascii=True, indent=2)
		logic_prompt = render_template(
			logic_prompt_template,
			ontologies=ontology_json,
			premises=premises_text,
		)
		logic_raw = logic_compiler.generate(logic_prompt)
		logic = parse_json(logic_raw)

		facts = ensure_str_list(logic.get("facts"), "facts")
		rules = ensure_str_list(logic.get("rules"), "rules")
		existentials = ensure_str_list(logic.get("existentials"), "existentials")

		symbols = Z3Symbols(sort=DeclareSort("U"))
		parser = FolParser(symbols)
		fact_exprs = [parser.parse(fact) for fact in facts]
		rule_exprs = [parser.parse(rule) for rule in rules]
		exist_exprs = [parser.parse(existential) for existential in existentials]

		solver = Solver()
		solver.add(*fact_exprs, *rule_exprs, *exist_exprs)
		result.update(
			{
				"premises-NL": premises,
				"ontology_output_raw": ontology_raw,
				"ontology_output": ontology,
				"logic_output_raw": logic_raw,
				"logic_output": logic,
				"status": str(solver.check()),
			}
		)
		return result
	except Exception as exc:
		result.update(
			{
				"premises-NL": result.get("premises-NL", sample.get("premises-NL", [])),
				"ontology_output_raw": result.get("ontology_output_raw"),
				"ontology_output": result.get("ontology_output"),
				"logic_output_raw": result.get("logic_output_raw"),
				"logic_output": result.get("logic_output"),
				"status": f"error: {type(exc).__name__}: {exc}",
			}
		)
		return result


def main() -> None:
    load_dotenv()
    logic_model_name = os.getenv("LOGIC_COMPILER_MODEL")
    ontology_model_name = os.getenv("ONTOLOGY_BUILDER_MODEL")
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        raise RuntimeError("HF_API_KEY is not set")
	
    if not logic_model_name or not ontology_model_name:
        raise RuntimeError(
            "Set LOGIC_COMPILER_MODEL and ONTOLOGY_BUILDER_MODEL in the environment."
        )

    ontology_instruction = load_text(INSTRUCTIONS_DIR / "ontology_builder.md")
    logic_instruction = load_text(INSTRUCTIONS_DIR / "logic_compiler.md")
    ontology_prompt_template = load_text(PROMPTS_DIR / "ontology_builder.md")
    logic_prompt_template = load_text(PROMPTS_DIR / "logic_compiler.md")

    ontology_builder = LLMClient(
        model_name=ontology_model_name,
        api_key=api_key,
        system_prompt=ontology_instruction,
        temperature=0.0,
    )
    logic_compiler = LLMClient(
        model_name=logic_model_name,
        api_key=api_key,
        system_prompt=logic_instruction,
        temperature=0.0,
    )

    data = json.loads(load_text(DATA_PATH))
    if not isinstance(data, list):
        raise TypeError("Expected a list in logic_based.json")

    sample_count = min(10, len(data))
    indices = random.sample(range(len(data)), k=sample_count)
    results: List[Dict[str, Any]] = []
    print(f"Processing {sample_count} samples...")

    for idx in indices:
        sample = data[idx]
        print(f"Processing sample index={idx}...")
        result = run_pipeline(
            sample,
            ontology_builder,
            logic_compiler,
            ontology_prompt_template,
            logic_prompt_template,
        )
        results.append(result)
        print(f"sample_index={idx} status={result['status']}")

    output_path = ROOT_DIR / "tests" / "parsing_outputs.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
	main()

