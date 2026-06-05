import json
import re
import z3
from src.llm import LLMClient
from src.logic.reasoning.parser import parse_formulas

def standardize_fol_formula(f_str: str) -> str:
    """Standardize logical operators and balance parentheses in an FOL formula string."""
    f_clean = f_str.strip()
    f_clean = (
        f_clean.replace("¬", "NOT ")
        .replace("∧", " AND ")
        .replace("∨", " OR ")
        .replace("→", " -> ")
        .replace("↔", " <-> ")
    )
    open_count = f_clean.count("(")
    close_count = f_clean.count(")")
    if close_count < open_count:
        f_clean = f_clean + ")" * (open_count - close_count)
    return f_clean

import threading

_z3_validation_lock = threading.Lock()

def validate_fol_formulas(formulas: list[str]) -> tuple[bool, str]:
    """Validate FOL formulas using Z3 parser."""
    if not formulas:
        return False, "No FOL formulas found."
    with _z3_validation_lock:
        try:
            standardized = [standardize_fol_formula(f) for f in formulas]
            symbols, exprs = parse_formulas(standardized)
            solver = z3.Solver()
            solver.set("timeout", 5000)
            for expr in exprs:
                solver.add(expr)
            solver.check()
            return True, ""
        except Exception as e:
            return False, str(e)



class HardNegativeAugmenter:
    """
    Handles Hard Negative Augmentation using LLM-assisted logical mutation.
    Leverages Qwen/Qwen3-235B-A22B-Instruct-2507 (via Together API) to make minimal,
    logically-decisive mutations to NL premises/conclusions and FOL formulas,
    updating the answer label accordingly, then validating the result using Z3.
    """
    def __init__(self, llm_client=None):
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(
                model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
                extra_body={"provider": "together"},
                temperature=0.1
            )
            # Force chat completions and correct Together provider routing
            self.llm_client.tokenizer = None

    def augment_sample(self, sample: dict, variant_idx: int = 0, max_retries: int = 3, validate_z3: bool = True) -> dict | None:
        """
        Generates a hard negative variant of a sample by logic mutation via Qwen3-235B.
        Validates the output with Z3 if validate_z3 is True. Returns the augmented sample or None on failure.
        """
        # Determine the key naming convention used in the input sample
        has_question = "question" in sample
        has_answer = "answer" in sample
        
        q_key = "question" if has_question else "conclusion"
        a_key = "answer" if has_answer else "label"
        
        orig_nl = sample.get("premises-NL", [])
        orig_fol = sample.get("premises-FOL", [])
        orig_q = sample.get(q_key, "")
        orig_a = sample.get(a_key, "")
        
        if not orig_nl or not orig_fol:
            return None

        # Build prompt
        prompt = self._build_prompt(orig_nl, orig_fol, orig_q, orig_a)
        
        for attempt in range(max_retries):
            try:
                response = self.llm_client.generate_text(prompt, max_new_tokens=4096)
                mutated = self._parse_response(response)
                if not mutated:
                    continue
                
                # Check structure
                mutated_nl = mutated.get("premises-NL", [])
                mutated_fol = mutated.get("premises-FOL", [])
                mutated_q = mutated.get("question", "")
                mutated_a = mutated.get("answer", "")
                
                if len(mutated_nl) != len(orig_nl) or len(mutated_fol) != len(orig_fol):
                    # Maintain 1:1 mapping count
                    continue
                
                # Validate FOL syntax with Z3
                if validate_z3:
                    is_valid, err = validate_fol_formulas(mutated_fol)
                    if not is_valid:
                        print(f"Z3 validation failed for mutated sample (attempt {attempt+1}): {err}")
                        continue
                
                # Ensure the answer is valid
                if mutated_a not in ["True", "False", "Unknown"]:
                    continue
                
                # Check that something actually changed compared to original
                if (mutated_nl == orig_nl and mutated_fol == orig_fol and mutated_q == orig_q and mutated_a == orig_a):
                    continue
                
                # Construct augmented sample, keeping original keys
                augmented = sample.copy()
                augmented["premises-NL"] = mutated_nl
                augmented["premises-FOL"] = mutated_fol
                augmented[q_key] = mutated_q
                augmented[a_key] = mutated_a
                
                # Update source metadata
                orig_source = sample.get("dataset_source", "unknown")
                augmented["dataset_source"] = f"{orig_source}-augmented-negative-var{variant_idx}"
                
                if "example_id" in sample:
                    augmented["example_id"] = f"{sample['example_id']}_neg_var{variant_idx}"
                    
                return augmented

                
            except Exception as e:
                print(f"Error during hard negative augmentation attempt {attempt+1}: {e}")
                
        return None

    def _build_prompt(self, nl_premises, fol_premises, question, answer):
        # Format the input sample for the prompt
        sample_str = json.dumps({
            "premises-NL": nl_premises,
            "premises-FOL": fol_premises,
            "question": question,
            "answer": answer
        }, indent=2, ensure_ascii=False)
        
        prompt = f"""You are a precise logical reasoning assistant and expert in First-Order Logic (FOL) and Z3 syntax.
Your task is to take a logic puzzle sample and generate a "hard negative" variant of it.

A "hard negative" is a modified version of the original sample where a small, logically-decisive change is made to one of the premises or to the question, such that the logical relationship (entailment) is flipped or changed, leading to a new correct answer.

Guidelines:
1. Select one premise or the question to modify.
2. Make a minimal logical change to its quantifier, connective, or negation. For example:
   - Change "all" to "some" or "no" (e.g. "All students like studying" -> "Some students like studying" or "No students like studying").
   - Change "some" to "all" or "none".
   - Add/remove negation "not" / "không".
   - Swap "and" / "or".
3. You MUST update BOTH the natural language (NL) and its corresponding First-Order Logic (FOL) formula so they remain perfectly aligned and representing the exact same meaning.
4. Keep all other premises, vocabulary, and predicates completely unchanged.
5. Re-evaluate the logical consequence of the modified premises + question and determine the correct new answer ("True", "False", or "Unknown").
6. Ensure the natural language remains grammatically correct and natural (in the same language as the input: English or Vietnamese).
7. Ensure the modified FOL formulas are valid Z3 formulas (correct parenthesis balance, standard uppercase operators: AND, OR, NOT, ->, <->, and quantifiers: ForAll(x, ...), Exists(x, ...)).

Input Sample:
{sample_str}

Respond with ONLY a valid JSON object in this format. No conversation, no markdown wrapper around the JSON:
{{
  "premises-NL": [ ... ],
  "premises-FOL": [ ... ],
  "question": "...",
  "answer": "..."
}}
"""
        return prompt

    def _parse_response(self, text):
        # Clean text and find json block
        json_str = ""
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start:end+1].strip()
            else:
                json_str = text.strip()
                
        try:
            return json.loads(json_str)
        except Exception:
            return None
