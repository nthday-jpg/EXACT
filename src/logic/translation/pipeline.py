import re
import json
import torch
from src.utils.normalization import extract_fol_formulas, normalize_logic_fol_entry
from src.logic.reasoning.verifier import try_parse_fol
from src.llm import LLMClient

class NLToFOLPipeline:
    """
    Pipeline that translates natural language premises and a conclusion
    into First-Order Logic (FOL) formulas.
    
    Supports both local execution (via Hugging Face LoRA models) and remote API execution.
    """
    def __init__(self, use_local: bool = True, model_dir: str = None, llm_client = None):
        self.use_local = use_local
        self.model_dir = model_dir
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(use_local=use_local, model_dir=model_dir)

    @property
    def tokenizer(self):
        return self.llm_client.tokenizer

    @tokenizer.setter
    def tokenizer(self, value):
        self.llm_client.tokenizer = value

    @property
    def model(self):
        return self.llm_client.model

    @model.setter
    def model(self, value):
        self.llm_client.model = value

    @property
    def device(self):
        return self.llm_client.device

    def load_local_model(self):
        self.llm_client.load_local_model()

    def _generate_text(self, system_prompt: str, user_prompt: str, max_new_tokens: int = 512) -> str:
        return self.llm_client.generate_text(user_prompt, system_prompt=system_prompt, max_new_tokens=max_new_tokens)



    def generate_glossary(self, nl_list: list[str]) -> dict | None:
        """Analyze natural language sentences and generate a unified JSON glossary of predicates and constants."""
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\n"
            
        system_prompt = (
            "You are a formal logic analyzer. Your task is to analyze a list of natural language statements "
            "and generate a unified Glossary of entities (constants) and predicates that will be used to translate them into First-Order Logic (FOL).\n\n"
            "Strictly follow these rules:\n"
            "1. Identify all unique predicates. A predicate represents a property or relation of one or more terms. "
            "Use camelCase or snake_case consistently for predicate names. E.g., isStudent(x) or is_student(x).\n"
            "2. Identify all unique constants (names of specific people, courses, events, objects, numbers). "
            "Constants must be singular, capitalized names or standardized symbols. E.g., Sophia, CourseA, Time800AM. "
            "Do not use spaces inside constant names; use underscores or camelCase. E.g., Course_A or CourseA.\n"
            "3. Keep the predicates and constants as simple, generic, and aligned as possible. If two statements refer to the same concept "
            "(e.g. 'curriculum has exercises' and 'curriculum features practical exercises'), they MUST map to the same predicate (e.g. has_exercises(c)).\n"
            "4. Output a STRICT valid JSON object with two keys: 'predicates' (a dictionary mapping the predicate signature to its English description) "
            "and 'constants' (a dictionary mapping the constant name to its English description).\n\n"
            "Example output format:\n"
            "{\n"
            "  \"predicates\": {\n"
            "    \"Human(x)\": \"x is a human\",\n"
            "    \"Mortal(x)\": \"x is mortal\"\n"
            "  },\n"
            "  \"constants\": {\n"
            "    \"Socrates\": \"Socrates\"\n"
            "  }\n"
            "}\n\n"
            "Return JSON only. Do not include markdown code block formatting (like ```json)."
        )
        
        user_prompt = (
            "Analyze the following natural language statements:\n"
            f"{nl_content.strip()}\n\n"
            "Generate the strict JSON Glossary. Return JSON only."
        )
        
        try:
            response = self._generate_text(system_prompt, user_prompt, max_new_tokens=512)
            # Clean markdown code block if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = re.sub(r"^```(?:json)?\n", "", cleaned_response)
                cleaned_response = re.sub(r"\n```$", "", cleaned_response)
            
            glossary = json.loads(cleaned_response.strip())
            if isinstance(glossary, dict) and ("predicates" in glossary or "constants" in glossary):
                return glossary
        except Exception:
            pass
        return None

    def translate_list(self, nl_list: list[str]) -> list[str]:
        """Translates a list of natural language sentences into FOL formulas in a single LLM call."""
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\n"
            
        user_prompt = (
            "Convert the following premises into canonical first-order logic.\n\n"
            "Premises:\n"
            f"{nl_content.strip()}\n\n"
            "Return a JSON list of strings containing the formulas."
        )
        
        # 1. Try to generate a unified glossary to enforce predicate/entity alignment
        glossary = self.generate_glossary(nl_list)
        
        if glossary:
            # Convert glossary to string for the prompt
            glossary_str = json.dumps(glossary, indent=2)
            system_prompt = (
                "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
                "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n\n"
                "ALLOWED OPERATORS:\n"
                "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
                "QUANTIFIER RULES:\n"
                "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
                "GLOSSARY CONSTRAINTS:\n"
                "You must strictly align your translation with the Glossary below.\n"
                "- Every constant name in your formulas must match a constant in the Glossary exactly (e.g. do not mix Sophia and sophia).\n"
                "- Every predicate must match a predicate signature in the Glossary exactly (e.g. do not mix isStudent(x) and Student(x)).\n"
                "- Do not introduce any new predicates or constants not defined in the Glossary.\n\n"
                f"Glossary:\n{glossary_str}\n\n"
                "Return JSON only."
            )
        else:
            # Fallback to standard prompt if glossary generation fails
            system_prompt = (
                "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
                "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n\n"
                "ALLOWED OPERATORS:\n"
                "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
                "QUANTIFIER RULES:\n"
                "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
                "Return JSON only."
            )
        
        response_content = self._generate_text(system_prompt, user_prompt, max_new_tokens=1024)
        all_extracted_fol = extract_fol_formulas(response_content)
        # Normalize each formula automatically to repair simple syntax and casing issues immediately
        all_extracted_fol = [normalize_logic_fol_entry(fol) for fol in all_extracted_fol]
        # Validate each formula and repair any that fail to parse
        all_extracted_fol = self._validate_and_repair(all_extracted_fol)
        return all_extracted_fol

    def _repair_fol(self, formula: str, error: str) -> str:
        """Ask the LLM to fix a broken FOL formula given a parse error message."""
        system_prompt = (
            "You are a first-order logic formula corrector.\n\n"
            "Fix the given FOL formula so it is accepted by a strict parser.\n\n"
            "ALLOWED OPERATORS: AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n"
            "QUANTIFIER SYNTAX: ForAll(x, <body>) or Exists(x, <body>)\n"
            "PREDICATE SYNTAX: P(x), R(a, b) — no spaces before '('\n"
            "Return ONLY the corrected formula string, no explanation."
        )
        user_prompt = (
            f"Broken FOL formula:\n{formula}\n\n"
            f"Parse error:\n{error}\n\n"
            "Return the corrected formula only."
        )
        return self._generate_text(system_prompt, user_prompt, max_new_tokens=256).strip()

    def _validate_and_repair(self, formulas: list[str], max_retries: int = 2) -> list[str]:
        """Validate each FOL formula by attempting a parse; repair broken ones via LLM.

        For each formula:
          1. Try to parse with Z3.
          2. If it fails, send (formula, error) to the LLM for repair.
          3. Repeat up to `max_retries` times, then keep whatever is available.
        """
        repaired: list[str] = []
        for formula in formulas:
            current = formula
            ok, err = try_parse_fol(current)
            for _ in range(max_retries):
                if ok:
                    break
                candidate = self._repair_fol(current, err)
                # Normalize the LLM repaired candidate to resolve minor formatting issues
                candidate = normalize_logic_fol_entry(candidate)
                new_ok, new_err = try_parse_fol(candidate)
                if new_ok or len(candidate) > 0:
                    # Accept repaired version even if still broken — it may be closer
                    current = candidate
                    ok, err = new_ok, new_err
            repaired.append(current)
        return repaired

    def translate_premises_and_conclusion(self, premises_nl: list[str], conclusion_nl: str) -> tuple[list[str], str]:
        """Translates natural language premises and conclusion into FOL formulas."""
        combined_nl_list = premises_nl + [conclusion_nl]
        all_extracted_fol = self.translate_list(combined_nl_list)
        
        expected_count = len(combined_nl_list)
        if len(all_extracted_fol) < expected_count:
            premises_fol = all_extracted_fol[:-1]
            conclusion_fol = all_extracted_fol[-1] if all_extracted_fol else ""
        else:
            premises_fol = all_extracted_fol[:len(premises_nl)]
            conclusion_fol = all_extracted_fol[len(premises_nl)]
            
        return premises_fol, conclusion_fol
