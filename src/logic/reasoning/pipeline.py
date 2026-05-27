import json
import re
import z3
from z3 import unsat, sat
import torch
from src.logic.reasoning.verifier import verify_with_z3, extract_proof_structure
from src.llm import LLMClient
from src.llm.prompts import (
    FILTER_PREMISES_SYSTEM_PROMPT,
    FILTER_PREMISES_USER_PROMPT_TEMPLATE,
    REASONING_SYSTEM_PROMPT,
    REASONING_UNSAT_USER_PROMPT_TEMPLATE,
    REASONING_SAT_USER_PROMPT_TEMPLATE,
    REASONING_UNKNOWN_USER_PROMPT_TEMPLATE,
    COT_SYSTEM_PROMPT,
    COT_UNSAT_USER_PROMPT_TEMPLATE,
    COT_SAT_USER_PROMPT_TEMPLATE,
    COT_UNKNOWN_USER_PROMPT_TEMPLATE,
)

class ReasoningPipeline:
    """
    Pipeline that takes First-Order Logic (FOL) formulas, verifies them mathematically
    using Z3 (via contradiction proof), and generates step-by-step natural language reasoning
    explaining the Z3 result (unsat core or counterexample).
    
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



    def verify(self, premises_fol: list[str], conclusion_fol: str, negate_conclusion: bool = True) -> dict:
        """Parses FOL formulas, tracks them in Z3 solver, and checks for entailment via contradiction."""
        return verify_with_z3(premises_fol, conclusion_fol, negate_conclusion=negate_conclusion)

    def filter_relevant_premises(
        self,
        premises_nl: list[str],
        conclusion_nl: str,
        premises_fol: list[str],
        top_k: int = None,
    ) -> tuple[list[str], list[str], list[int]]:
        """Use LLM to select the subset of premises most relevant to the conclusion.

        Returns:
            (filtered_premises_nl, filtered_premises_fol, selected_indices)

        Falls back to all premises when:
        - There are 3 or fewer premises (not worth the LLM call).
        - The LLM response cannot be parsed.
        - Fewer than 2 premises survive filtering (degenerate result).
        """
        n = len(premises_nl)
        if n <= 3:
            return premises_nl, premises_fol, list(range(n))

        if top_k is None:
            # Keep at least half of the premises, minimum 3
            top_k = max(3, (n + 1) // 2)

        numbered = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(premises_nl))
        system_prompt = FILTER_PREMISES_SYSTEM_PROMPT
        user_prompt = FILTER_PREMISES_USER_PROMPT_TEMPLATE.format(
            numbered=numbered, conclusion_nl=conclusion_nl, top_k=top_k
        )

        try:
            response = self._generate_text(system_prompt, user_prompt, max_new_tokens=128)
            match = re.search(r"\[[\d,\s]+\]", response)
            if not match:
                return premises_nl, premises_fol, list(range(n))
            indices_1based: list[int] = json.loads(match.group())
            # Convert to 0-based, deduplicate, clamp to valid range
            indices = sorted({i - 1 for i in indices_1based if 1 <= i <= n})
            if len(indices) < 2:
                return premises_nl, premises_fol, list(range(n))
            filtered_nl = [premises_nl[i] for i in indices]
            filtered_fol = [premises_fol[i] for i in indices] if len(premises_fol) == n else premises_fol
            return filtered_nl, filtered_fol, indices
        except Exception:
            return premises_nl, premises_fol, list(range(n))

    def generate_reasoning(self, premises_nl: list[str], conclusion_nl: str, verification: dict) -> str:
        """Generates step-by-step reasoning explaining the Z3 verification result."""
        result = verification["result"]

        if result == unsat:
            # Extract indices from unsat core
            core_indices = []
            for var_str in verification["unsat_core"]:
                if var_str.startswith("p_"):
                    try:
                        idx = int(var_str.split("_")[1]) - 1
                        core_indices.append(idx)
                    except ValueError:
                        pass
            core_indices.sort()

            # Format core premises list
            core_premises_nl = []
            for idx in core_indices:
                core_premises_nl.append(f"- Premise {idx+1}: {premises_nl[idx]}")
            core_premises_text = "\n".join(core_premises_nl) if core_premises_nl else "\n".join(f"- {p}" for p in premises_nl)

            user_prompt = REASONING_UNSAT_USER_PROMPT_TEMPLATE.format(
                core_premises_text=core_premises_text,
                conclusion_nl=conclusion_nl
            )
        elif result == sat:
            model_str = str(verification["model"])
            premises_text = "\n".join(f"- {p}" for p in premises_nl)
            user_prompt = REASONING_SAT_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                conclusion_nl=conclusion_nl,
                model_str=model_str
            )
        else:
            premises_text = "\n".join(f"- {p}" for p in premises_nl)
            user_prompt = REASONING_UNKNOWN_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                conclusion_nl=conclusion_nl
            )

        system_prompt = REASONING_SYSTEM_PROMPT

        return self._generate_text(system_prompt, user_prompt, max_new_tokens=1024)

    # ------------------------------------------------------------------
    # Structured Chain-of-Thought output
    # ------------------------------------------------------------------

    def _parse_cot_steps(self, text: str) -> list[str]:
        """Extract numbered reasoning steps from LLM output into a clean list.

        Tries three increasingly lenient patterns:
        1. Explicit ``Step N:`` / ``Step N.`` labels.
        2. Plain numbered list items (``1.``, ``2)``).
        3. Non-empty lines as a last resort.
        """
        # Pattern 1: "Step N: ..." or "Step N. ..."
        steps = re.findall(
            r"(?:^|\n)\s*Step\s+\d+[:.]\s*(.+?)(?=\n\s*Step\s+\d+[:.:]|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        steps = [s.strip() for s in steps if s.strip()]
        if steps:
            return steps

        # Pattern 2: plain numbered list
        steps = re.findall(
            r"(?:^|\n)\s*\d+[.)]\s*(.+?)(?=\n\s*\d+[.)]|\Z)",
            text,
            re.DOTALL,
        )
        steps = [s.strip() for s in steps if s.strip()]
        if steps:
            return steps

        # Pattern 3: fallback — one non-empty line per step
        return [line.strip() for line in text.splitlines() if line.strip()]

    def generate_cot(
        self,
        premises_nl: list[str],
        conclusion_nl: str,
        verification: dict,
    ) -> tuple[str, list[str]]:
        """Generate structured Chain-of-Thought reasoning.

        Uses the same contextual prompts as ``generate_reasoning()`` but
        instructs the LLM to format its answer as explicit numbered steps
        (``Step 1: ...``, ``Step 2: ...``, etc.).

        Returns:
            ``(reasoning_str, cot_steps)`` where ``reasoning_str`` is the raw
            LLM response (backward-compatible with the ``reasoning`` field) and
            ``cot_steps`` is a parsed list of individual reasoning steps.
        """
        result = verification["result"]

        if result == unsat:
            core_indices = []
            for var_str in verification["unsat_core"]:
                if var_str.startswith("p_"):
                    try:
                        core_indices.append(int(var_str.split("_")[1]) - 1)
                    except ValueError:
                        pass
            core_indices.sort()

            core_premises_nl = [
                f"- Premise {i + 1}: {premises_nl[i]}"
                for i in core_indices
                if i < len(premises_nl)
            ]
            core_premises_text = (
                "\n".join(core_premises_nl)
                if core_premises_nl
                else "\n".join(f"- {p}" for p in premises_nl)
            )
            proof_structure = ""
            if "proof" in verification and verification["proof"] is not None:
                proof_structure = extract_proof_structure(verification["proof"])

            proof_skeleton_instruction = ""
            if proof_structure:
                proof_skeleton_instruction = (
                    f"The formal Z3 SMT solver generated this mathematical proof skeleton:\n"
                    f"{proof_structure}\n\n"
                    f"Your explanation MUST strictly match this proof skeleton. "
                    f"Ensure every step in your CoT corresponds to a deduction step in the Z3 proof tree, "
                    f"making the logic mathematically grounded."
                )

            user_prompt = COT_UNSAT_USER_PROMPT_TEMPLATE.format(
                core_premises_text=core_premises_text,
                conclusion_nl=conclusion_nl,
                proof_skeleton_instruction=proof_skeleton_instruction
            )
        elif result == sat:
            model_str = str(verification["model"])
            premises_text = "\n".join(f"- {p}" for p in premises_nl)
            user_prompt = COT_SAT_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                conclusion_nl=conclusion_nl,
                model_str=model_str
            )
        else:
            premises_text = "\n".join(f"- {p}" for p in premises_nl)
            user_prompt = COT_UNKNOWN_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                conclusion_nl=conclusion_nl
            )

        system_prompt = COT_SYSTEM_PROMPT

        raw_text = self._generate_text(system_prompt, user_prompt, max_new_tokens=1024)
        cot_steps = self._parse_cot_steps(raw_text)
        return raw_text, cot_steps
