import os
import re
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from src.llm import LLMClient
from src.data.cleaning.validator import validate_sample_fol
from src.data.cleaning.prompts import (
    STANDARD_REPAIR_SYSTEM_PROMPT,
    STANDARD_REPAIR_USER_TEMPLATE,
    FEEDBACK_REPAIR_TEMPLATE,
    DEEP_REPAIR_SYSTEM_PROMPT,
    DIAGNOSTIC_SYSTEM_PROMPT,
    DIAGNOSTIC_USER_TEMPLATE,
)


class LogicalDatasetRepairer:
    """
    Handles LLM-assisted logical sample corrections, including feedback-guided turns,
    deep SMT parser rule corrections, and technical fallback diagnostics generation.
    """
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def _call_llm_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Utility to invoke LLM and safely parse the JSON response."""
        try:
            response_text = self.llm_client.generate_text(
                user_prompt,
                system_prompt=system_prompt,
                max_new_tokens=2048
            )
        except Exception as e:
            print(f"      - LLM call failed: {e}")
            return None

        # Clean JSON markdown blocks
        json_str = ""
        match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            start = response_text.find("{")
            end = response_text.rfind("}")
            if start != -1 and end != -1:
                json_str = response_text[start:end+1].strip()
            else:
                json_str = response_text.strip()

        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"      - Failed to parse JSON response: {e}")
            return None

    def repair_sample(self, sample: Dict[str, Any], max_retries: int = 3) -> Tuple[bool, Dict[str, Any]]:
        """
        Attempt to repair an invalid sample using Standard Repair, fallback to Deep Repair,
        and finally generate diagnostic analysis on total failure.
        """
        ex_id = sample.get("example_id", "unknown")
        
        # --- STAGE 1: Standard Conversational Repair ---
        print(f"    [Standard Repair] Triggering turn-based feedback repair...")
        messages = [
            {"role": "system", "content": STANDARD_REPAIR_SYSTEM_PROMPT},
            {"role": "user", "content": STANDARD_REPAIR_USER_TEMPLATE.format(sample_json=json.dumps(sample, indent=2, ensure_ascii=False))}
        ]

        repaired_sample = None
        current_error = sample.get("validation_error", "Unknown validation error")

        for turn in range(1, max_retries + 1):
            user_prompt = messages[-1]["content"] if turn > 1 else messages[1]["content"]
            repaired_sample = self._call_llm_json(STANDARD_REPAIR_SYSTEM_PROMPT, user_prompt)
            if not repaired_sample or not isinstance(repaired_sample, dict):
                print(f"      - Turn {turn}: LLM did not return a valid JSON object.")
                continue

            # Quantifier brackets cleanup
            rep_formulas = repaired_sample.get("premises-FOL", [])
            cleaned_formulas = []
            for f in rep_formulas:
                f_clean = re.sub(r"\b(ForAll|Exists)\(\s*\[\s*([a-zA-Z_]\w*)\s*\]\s*,", r"\1(\2,", f)
                match_multi = re.search(r"\b(ForAll|Exists)\(\s*\[\s*([a-zA-Z_]\w*)\s*,\s*([a-zA-Z_]\w*)\s*\]\s*,", f_clean)
                if match_multi:
                    q, v1, v2 = match_multi.groups()
                    f_clean = re.sub(r"\b(ForAll|Exists)\(\s*\[\s*[a-zA-Z_]\w*\s*,\s*[a-zA-Z_]\w*\s*\]\s*,", f"{q}({v1}, {q}({v2},", f_clean) + ")"
                cleaned_formulas.append(f_clean)
            repaired_sample["premises-FOL"] = cleaned_formulas

            # Syntax checker
            forbidden = []
            for f in cleaned_formulas:
                if "/" in f: forbidden.append(f"Contains division '/': {f}")
                if "*" in f: forbidden.append(f"Contains multiplication '*': {f}")
                if "[" in f or "]" in f: forbidden.append(f"Contains brackets []: {f}")

            # Check length matching
            nl_len = len(repaired_sample.get("premises-NL", []))
            fol_len = len(cleaned_formulas)

            if nl_len != fol_len:
                current_error = (
                    f"Mismatched premise counts: premises-NL has {nl_len} elements, "
                    f"but premises-FOL has {fol_len} elements. They must have the exact same number of elements."
                )
                is_valid = False
            elif forbidden:
                current_error = "Forbidden syntax check failed:\n" + "\n".join(forbidden)
                is_valid = False
            else:
                is_valid, current_error = validate_sample_fol(cleaned_formulas)

            if is_valid:
                print(f"      - [SUCCESS] Standard Repair succeeded at turn {turn}!")
                repaired_sample.pop("validation_error", None)
                return True, repaired_sample

            # Record feedback and try again
            feedback = FEEDBACK_REPAIR_TEMPLATE.format(error_msg=current_error)
            messages.append({"role": "assistant", "content": json.dumps(repaired_sample)})
            messages.append({"role": "user", "content": feedback})

        # --- STAGE 2: Deep Repair fallback ---
        print(f"    [Deep Repair] Standard repair failed. Triggering deep SMT parser repair...")
        deep_user_prompt = f"Failed sample:\n{json.dumps(sample, indent=2)}\n\nLast validation error: {current_error}"
        repaired_sample = self._call_llm_json(DEEP_REPAIR_SYSTEM_PROMPT, deep_user_prompt)

        if repaired_sample and isinstance(repaired_sample, dict):
            rep_formulas = repaired_sample.get("premises-FOL", [])
            cleaned_formulas = []
            for f in rep_formulas:
                f_clean = re.sub(r"\b(ForAll|Exists)\(\s*\[\s*([a-zA-Z_]\w*)\s*\]\s*,", r"\1(\2,", f)
                cleaned_formulas.append(f_clean)
            repaired_sample["premises-FOL"] = cleaned_formulas

            # Check length matching in Deep Repair
            nl_len = len(repaired_sample.get("premises-NL", []))
            fol_len = len(cleaned_formulas)
            if nl_len != fol_len:
                is_valid = False
                current_error = (
                    f"Mismatched premise counts: premises-NL has {nl_len} elements, "
                    f"but premises-FOL has {fol_len} elements. They must have the exact same number of elements."
                )
            else:
                is_valid, current_error = validate_sample_fol(cleaned_formulas)

            if is_valid:
                print(f"      - [SUCCESS] Deep Repair succeeded in resolving type mismatches!")
                repaired_sample.pop("validation_error", None)
                return True, repaired_sample

        # --- STAGE 3: Diagnostic analysis fallback ---
        print(f"    [Fallback Diagnostics] Repair failed. Generating technical root cause analysis...")
        diag_user = DIAGNOSTIC_USER_TEMPLATE.format(sample_json=json.dumps(sample, indent=2))
        diag_report = self._call_llm_json(DIAGNOSTIC_SYSTEM_PROMPT, diag_user)

        # Write to diagnostics report file
        diag_file = Path("data/processed/pipeline_diagnostics.md")
        os.makedirs(diag_file.parent, exist_ok=True)
        
        diag_exists = diag_file.exists()
        with open(diag_file, "a", encoding="utf-8") as df:
            if not diag_exists:
                df.write("# 🔍 Automated Logic Repair Diagnostics & Strategies Report\n\n")
                df.write("This report is generated dynamically by the LogicalDatasetPipeline when a sample fails auto-repair.\n\n")
            
            df.write(f"## ❌ Sample {ex_id}\n\n")
            df.write(f"- **Z3 Error**: `{current_error}`\n")
            if diag_report:
                df.write(f"- **Root Cause Analysis**: {diag_report.get('root_cause_analysis', 'N/A')}\n")
                df.write(f"- **Recommended Steps**: {diag_report.get('repair_steps', 'N/A')}\n")
                df.write(f"- **Suggested Repair FOL**:\n  ```json\n  {json.dumps(diag_report.get('repaired_premises_fol', []), indent=2)}\n  ```\n\n")
            else:
                df.write("- **Root Cause**: Could not parse structured diagnostics. SMT sort collision or arithmetic constraint violation remains.\n\n")

        bad_result = sample.copy()
        bad_result["validation_error"] = f"Failed to repair. Technical diagnostics appended to {diag_file.name}."
        return False, bad_result
