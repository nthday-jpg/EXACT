import re
import json
import torch
from src.utils.normalization import extract_fol_formulas, normalize_logic_fol_entry, unify_fol_predicates
from src.logic.reasoning.verifier import try_parse_fol
from src.llm import LLMClient
from src.llm.prompts import (
    GLOSSARY_SYSTEM_PROMPT,
    GLOSSARY_USER_PROMPT_TEMPLATE,
    TRANSLATE_USER_PROMPT_TEMPLATE,
    TRANSLATE_SYSTEM_PROMPT_GLOSSARY_TEMPLATE,
    TRANSLATE_SYSTEM_PROMPT_FALLBACK,
    REPAIR_FOL_SYSTEM_PROMPT,
    REPAIR_FOL_USER_PROMPT_TEMPLATE,
    COMBINED_GLOSSARY_AND_TRANSLATION_SYSTEM_PROMPT,
    COMBINED_GLOSSARY_AND_TRANSLATION_USER_PROMPT_TEMPLATE,
)

class NLToFOLPipeline:
    """
    Pipeline that translates natural language premises and a conclusion
    into First-Order Logic (FOL) formulas.
    
    Supports both local execution (via Hugging Face LoRA models) and remote API execution.
    """
    def __init__(self, use_local: bool = True, model_dir: str = None, llm_client = None, temperature: float = 0.1):
        self.use_local = use_local
        self.model_dir = model_dir
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(use_local=use_local, model_dir=model_dir, temperature=temperature)

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
            response = self._generate_text(system_prompt, user_prompt, max_new_tokens=1024)
            # Clean markdown code block if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = re.sub(r"^```(?:json)?\n", "", cleaned_response)
                cleaned_response = re.sub(r"\n```$", "", cleaned_response)
            
            # Safely locate the JSON dictionary block in case the LLM adds conversational wrappers
            json_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
            glossary_str = json_match.group(0) if json_match else cleaned_response
            
            glossary = json.loads(glossary_str.strip())
            if isinstance(glossary, dict) and ("predicates" in glossary or "constants" in glossary):
                return glossary
        except Exception:
            pass
        return None

    def extract_glossary_from_fol(self, formulas: list[str]) -> str:
        """Extract predicates and constants from a list of FOL formulas to construct a glossary context string."""
        predicates = set()
        constants = set()
        reserved = {"ForAll", "Exists", "AND", "OR", "NOT", "In", "implies", "BICOND", "IMPLIES"}
        
        for formula in formulas:
            if not formula:
                continue
            # Find predicate/function calls like Name(...)
            calls = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)", formula)
            for name, args_str in calls:
                if name in reserved:
                    continue
                args = [a.strip() for a in args_str.split(",") if a.strip()]
                arity = len(args)
                predicates.add(f"{name}({', '.join(['x']*arity)})")
                
                for arg in args:
                    if arg not in {"x", "y", "z", "w", "u", "v", "a", "b", "c"} and not arg.isdigit():
                        constants.add(arg)
                        
            # Find constants in comparisons
            comp_matches = re.findall(r"(=|!=|>=|<=|>|<)\s*([A-Za-z0-9_']+)", formula)
            for op, val in comp_matches:
                val = val.strip().strip("'")
                if val and not val.isdigit() and val not in {"x", "y", "z", "w", "u", "v", "a", "b", "c"}:
                    constants.add(val)
                    
        pred_str = ", ".join(sorted(list(predicates)))
        const_str = ", ".join(sorted(list(constants)))
        return f"Predicates: {pred_str}\nConstants: {const_str}"

    def translate_list(self, nl_list: list[str], max_new_tokens: int = None, glossary_str: str = None) -> list[str]:
        """Translates a list of natural language sentences into FOL formulas.
        Uses a combined single LLM call for both glossary generation and translation
        (Prompt Batching) to reduce API roundtrips and improve alignment.
        Falls back to two-stage translation if the combined call fails to parse.
        """
        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\n"

        # Determine if we should bypass the glossary (e.g., if using the finetuned model Qwen3-8B LoRA which was trained on direct flat translation)
        is_finetuned = False
        if hasattr(self.llm_client, "model_name") and self.llm_client.model_name:
            model_name_lower = self.llm_client.model_name.lower()
            if "exact-qwen" in model_name_lower or "lora" in model_name_lower or "finetune" in model_name_lower:
                is_finetuned = True

        # If a glossary is explicitly provided, we run the translation strictly under its constraints
        if glossary_str:
            if is_finetuned:
                system_prompt = (
                    "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
                    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n"
                    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\n\n"
                    "ALLOWED OPERATORS:\n"
                    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
                    "QUANTIFIER RULES:\n"
                    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
                    "GLOSSARY CONSTRAINTS:\n"
                    "You MUST strictly align your translation with the predicates and constants used in the premises:\n"
                    f"{glossary_str}\n\n"
                    "Return JSON only."
                )
            else:
                system_prompt = TRANSLATE_SYSTEM_PROMPT_GLOSSARY_TEMPLATE.format(glossary_str=glossary_str)
                
            user_prompt = TRANATE_USER_PROMPT_TEMPLATE = TRANSLATE_USER_PROMPT_TEMPLATE.format(
                nl_content=nl_content.strip(),
                num_premises=len(nl_list)
            )
            
            _max_tokens = max_new_tokens if max_new_tokens is not None else (4096 if not self.use_local else 1024)
            try:
                response_content = self._generate_text(system_prompt, user_prompt, max_new_tokens=_max_tokens)
                all_extracted_fol = extract_fol_formulas(response_content)
                all_extracted_fol = [normalize_logic_fol_entry(fol) for fol in all_extracted_fol]
                all_extracted_fol = self._validate_and_repair(all_extracted_fol)
                return unify_fol_predicates(all_extracted_fol)
            except Exception as e:
                print(f"Warning: Glossary-constrained translation failed ({str(e)}). Falling back to standard pipeline.")

        if is_finetuned:
            # Direct translation using the fine-tuned model's exact training prompt (No Glossary, 1 LLM call)
            system_prompt = TRANSLATE_SYSTEM_PROMPT_FALLBACK
            user_prompt = TRANSLATE_USER_PROMPT_TEMPLATE.format(
                nl_content=nl_content.strip(),
                num_premises=len(nl_list)
            )
            # Use larger token budget on remote calls to prevent truncation by thinking blocks
            _max_tokens = max_new_tokens if max_new_tokens is not None else (4096 if not self.use_local else 1024)
            try:
                response_content = self._generate_text(system_prompt, user_prompt, max_new_tokens=_max_tokens)
                all_extracted_fol = extract_fol_formulas(response_content)
                all_extracted_fol = [normalize_logic_fol_entry(fol) for fol in all_extracted_fol]
                all_extracted_fol = self._validate_and_repair(all_extracted_fol)
                return unify_fol_predicates(all_extracted_fol)
            except Exception as e:
                print(f"Warning: Direct translation failed ({str(e)}). Falling back to standard pipeline.")


        # Try unified combined glossary and translation in a single LLM call
        try:
            system_prompt = COMBINED_GLOSSARY_AND_TRANSLATION_SYSTEM_PROMPT
            user_prompt = COMBINED_GLOSSARY_AND_TRANSLATION_USER_PROMPT_TEMPLATE.format(nl_content=nl_content.strip())
            
            response_content = self._generate_text(system_prompt, user_prompt, max_new_tokens=(4096 if not self.use_local else 2048))
            cleaned_response = response_content.strip()
            
            # Clean markdown code block if present
            if cleaned_response.startswith("```"):
                cleaned_response = re.sub(r"^```(?:json)?\n", "", cleaned_response)
                cleaned_response = re.sub(r"\n```$", "", cleaned_response)
            
            # Safely locate the JSON dictionary block in case the LLM adds conversational wrappers
            json_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
            json_str = json_match.group(0) if json_match else cleaned_response
            
            combined_data = json.loads(json_str.strip())
            if isinstance(combined_data, dict) and "formulas" in combined_data:
                all_extracted_fol = combined_data["formulas"]
                if len(all_extracted_fol) > 0:
                    # Normalize and repair
                    all_extracted_fol = [normalize_logic_fol_entry(fol) for fol in all_extracted_fol]
                    all_extracted_fol = self._validate_and_repair(all_extracted_fol)
                    return unify_fol_predicates(all_extracted_fol)
        except Exception as e:
            # If the combined call fails, print a warning and fallback gracefully to the original two-stage flow
            print(f"Warning: Combined glossary and translation failed ({str(e)}). Falling back to two-stage translation.")

        # --- Fallback to original two-stage flow ---
        user_prompt = TRANSLATE_USER_PROMPT_TEMPLATE.format(
            nl_content=nl_content.strip(),
            num_premises=len(nl_list)
        )
        
        # 1. Try to generate a unified glossary to enforce predicate/entity alignment
        glossary = self.generate_glossary(nl_list)
        
        if glossary:
            # Convert glossary to string for the prompt
            glossary_str = json.dumps(glossary, indent=2)
            system_prompt = TRANSLATE_SYSTEM_PROMPT_GLOSSARY_TEMPLATE.format(glossary_str=glossary_str)
        else:
            # Fallback to standard prompt if glossary generation fails
            system_prompt = TRANSLATE_SYSTEM_PROMPT_FALLBACK
        
        response_content = self._generate_text(system_prompt, user_prompt, max_new_tokens=(4096 if not self.use_local else 2048))
        all_extracted_fol = extract_fol_formulas(response_content)
        # Normalize each formula automatically to repair simple syntax and casing issues immediately
        all_extracted_fol = [normalize_logic_fol_entry(fol) for fol in all_extracted_fol]
        # Validate each formula and repair any that fail to parse
        all_extracted_fol = self._validate_and_repair(all_extracted_fol)
        return unify_fol_predicates(all_extracted_fol)

    def _repair_fol(self, formula: str, error: str) -> str:
        """Ask the LLM to fix a broken FOL formula given a parse error message."""
        system_prompt = REPAIR_FOL_SYSTEM_PROMPT
        user_prompt = REPAIR_FOL_USER_PROMPT_TEMPLATE.format(formula=formula, error=error)
        return self._generate_text(system_prompt, user_prompt, max_new_tokens=256).strip()

    def _validate_and_repair_single(self, formula: str, max_retries: int = 2) -> str:
        """Validate and repair a single FOL formula."""
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
        return current

    def _validate_and_repair(self, formulas: list[str], max_retries: int = 2) -> list[str]:
        """Validate each FOL formula by attempting a parse; repair broken ones via LLM in parallel.

        For each formula:
          1. Try to parse with Z3.
          2. If it fails, send (formula, error) to the LLM for repair in parallel.
          3. Repeat up to `max_retries` times, then keep whatever is available.
        """
        import concurrent.futures
        
        # Parallelize the repair of multiple formulas
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(formulas) + 1, 8)) as executor:
            # Map single validation and repair over formulas
            results = list(executor.map(lambda f: self._validate_and_repair_single(f, max_retries), formulas))
        return results

    @staticmethod
    def _strip_question_framing(text: str) -> str:
        """Remove Yes/No question wrappers from a conclusion string.
        
        Converts patterns like:
          "Does it follow that X?" → "X"
          "Is it true that X?" → "X"
          "Can we conclude that X?" → "X"
        """
        import re
        stripped = text.strip()
        # Match common Yes/No question prefixes
        patterns = [
            r"^(?:does it follow that|is it true that|can we conclude that|is it the case that"
            r"|do the premises imply that|does the passage imply that"
            r"|does it follow from the premises that)\s*",
        ]
        for pat in patterns:
            m = re.match(pat, stripped, re.IGNORECASE)
            if m:
                stripped = stripped[m.end():]
                break
        # Remove trailing question mark
        stripped = stripped.rstrip("?").strip()
        # Capitalize first letter
        if stripped:
            stripped = stripped[0].upper() + stripped[1:]
        return stripped

    def translate_premises_and_conclusion(self, premises_nl: list[str], conclusion_nl: str) -> tuple[list[str], str]:
        """Translates natural language premises and conclusion into FOL formulas using a robust fallback."""
        # Strip question framing from Yes/No conclusions before translation
        # e.g. "Does it follow that X?" → "X" — prevents model from generating garbage biconditionals
        conclusion_for_translation = self._strip_question_framing(conclusion_nl)

        combined_nl_list = premises_nl + [conclusion_for_translation]
        all_extracted_fol = self.translate_list(combined_nl_list)
        
        expected_count = len(combined_nl_list)
        if len(all_extracted_fol) == expected_count:
            premises_fol = all_extracted_fol[:len(premises_nl)]
            conclusion_fol = all_extracted_fol[len(premises_nl)]
        else:
            # Sequential fallback: translate premises, extract glossary, and translate conclusion under constraints
            print(f"Warning: Combined translation length mismatch ({len(all_extracted_fol)} vs {expected_count}). Falling back to sequential glossary-aligned translation.")
            premises_fol = []
            for p_nl in premises_nl:
                res_list = self.translate_list([p_nl])
                premises_fol.append(res_list[0] if res_list else "")
            
            glossary_str = self.extract_glossary_from_fol(premises_fol)
            try:
                res_conclusion = self.translate_list([conclusion_for_translation], glossary_str=glossary_str)
            except TypeError:
                res_conclusion = self.translate_list([conclusion_for_translation])
            conclusion_fol = res_conclusion[0] if res_conclusion else ""
            
        return premises_fol, conclusion_fol






