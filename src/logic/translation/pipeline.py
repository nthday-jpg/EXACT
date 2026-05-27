import re
import json
import torch
from src.utils.normalization import extract_fol_formulas, normalize_logic_fol_entry
from src.logic.reasoning.verifier import try_parse_fol
from src.llm import LLMClient
from src.logic.prompts import (
    GLOSSARY_SYSTEM_PROMPT,
    GLOSSARY_USER_PROMPT_TEMPLATE,
    TRANSLATE_USER_PROMPT_TEMPLATE,
    TRANSLATE_SYSTEM_PROMPT_GLOSSARY_TEMPLATE,
    TRANSLATE_SYSTEM_PROMPT_FALLBACK,
    REPAIR_FOL_SYSTEM_PROMPT,
    REPAIR_FOL_USER_PROMPT_TEMPLATE,
)

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
            
        system_prompt = GLOSSARY_SYSTEM_PROMPT
        
        user_prompt = GLOSSARY_USER_PROMPT_TEMPLATE.format(nl_content=nl_content.strip())
        
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
            
        user_prompt = TRANSLATE_USER_PROMPT_TEMPLATE.format(nl_content=nl_content.strip())
        
        # 1. Try to generate a unified glossary to enforce predicate/entity alignment
        glossary = self.generate_glossary(nl_list)
        
        if glossary:
            # Convert glossary to string for the prompt
            glossary_str = json.dumps(glossary, indent=2)
            system_prompt = TRANSLATE_SYSTEM_PROMPT_GLOSSARY_TEMPLATE.format(glossary_str=glossary_str)
        else:
            # Fallback to standard prompt if glossary generation fails
            system_prompt = TRANSLATE_SYSTEM_PROMPT_FALLBACK
        
        response_content = self._generate_text(system_prompt, user_prompt, max_new_tokens=1024)
        all_extracted_fol = extract_fol_formulas(response_content)
        # Normalize each formula automatically to repair simple syntax and casing issues immediately
        all_extracted_fol = [normalize_logic_fol_entry(fol) for fol in all_extracted_fol]
        # Validate each formula and repair any that fail to parse
        all_extracted_fol = self._validate_and_repair(all_extracted_fol)
        return all_extracted_fol

    def _repair_fol(self, formula: str, error: str) -> str:
        """Ask the LLM to fix a broken FOL formula given a parse error message."""
        system_prompt = REPAIR_FOL_SYSTEM_PROMPT
        user_prompt = REPAIR_FOL_USER_PROMPT_TEMPLATE.format(formula=formula, error=error)
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
