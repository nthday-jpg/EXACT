import json
import re
import z3
from z3 import unsat, sat
import torch
from src.logic.reasoning.verifier import verify_with_z3, extract_proof_structure

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
        self.llm_client = llm_client
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None

    def load_local_model(self):
        """Loads Hugging Face tokenizer and PEFT LoRA model locally with NF4 4-bit quantization."""
        if not self.use_local:
            return
            
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        from pathlib import Path
        
        # Resolve default model directory if none provided
        if not self.model_dir:
            root_dir = Path(__file__).resolve().parents[3]
            self.model_dir = str(root_dir / "results")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-8B",
            quantization_config=bnb_config if torch.cuda.is_available() else None,
            device_map="cuda:0" if torch.cuda.is_available() else None,
            trust_remote_code=True,
            attn_implementation="sdpa" if torch.cuda.is_available() else None
        )
        
        self.model = PeftModel.from_pretrained(base_model, self.model_dir)
        self.model.eval()

    def _generate_text(self, system_prompt: str, user_prompt: str, max_new_tokens: int = 512) -> str:
        """Helper to generate text using either the local model or the LLM client."""
        if self.use_local:
            if not self.model:
                self.load_local_model()
                
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            chat_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            inputs = self.tokenizer(chat_prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id
                )
                
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            return response.strip()
        else:
            if not self.llm_client:
                raise ValueError("An LLMClient instance must be provided when use_local=False")
            
            # Temporarily override LLMClient's system prompt if necessary
            orig_system_prompt = self.llm_client.system_prompt
            self.llm_client.system_prompt = system_prompt
            
            try:
                res = self.llm_client.generate(user_prompt, max_tokens=max_new_tokens)
                return res["content"]
            finally:
                self.llm_client.system_prompt = orig_system_prompt

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
        system_prompt = (
            "You are a logical reasoning assistant. "
            "Identify which premises are directly needed to prove or disprove the given conclusion.\n\n"
            "Return ONLY a JSON list of 1-based premise numbers. Example: [1, 3, 5]"
        )
        user_prompt = (
            f"Premises:\n{numbered}\n\n"
            f"Conclusion:\n{conclusion_nl}\n\n"
            f"Select at most {top_k} premise numbers that are most relevant. "
            "Return a JSON list of integers only."
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

            user_prompt = (
                f"The following premises have been formally proven (via Z3 SMT solver) to entail the conclusion.\n\n"
                f"Key premises:\n"
                f"{core_premises_text}\n\n"
                f"Conclusion:\n"
                f"- {conclusion_nl}\n\n"
                f"Write a concise explanation that shows HOW these premises chain together to reach the conclusion. "
                f"Trace the logical flow: what does each premise contribute? How do they combine? "
                f"Use natural transitions like 'Since', 'Therefore', 'This means', 'Combined with', 'As a result'. "
                f"Do NOT simply restate or copy the premises — synthesize them into a coherent argument."
            )
        elif result == sat:
            model_str = str(verification["model"])
            user_prompt = (
                f"The SMT solver found a counterexample: the premises are all TRUE yet the conclusion is FALSE.\n\n"
                f"Premises:\n"
                f"{chr(10).join(f'- {p}' for p in premises_nl)}\n\n"
                f"Conclusion being tested:\n"
                f"- {conclusion_nl}\n\n"
                f"Counterexample (Z3 model):\n"
                f"{model_str}\n\n"
                f"Explain in plain language why this counterexample breaks the conclusion. "
                f"Show what the counterexample tells us, why it matters, and what logical gap it exposes. "
                f"Speak like a human who understands the argument — do not just restate the premises."
            )
        else:
            user_prompt = (
                f"The solver could not determine whether the conclusion is entailed by the premises.\n\n"
                f"Premises:\n"
                f"{chr(10).join(f'- {p}' for p in premises_nl)}\n\n"
                f"Conclusion:\n"
                f"- {conclusion_nl}\n\n"
                f"Analyse why the relationship is indeterminate. What information is missing? "
                f"What would need to be true for the conclusion to follow? "
                f"Write as a human reasoner, not as a list of facts."
            )

        system_prompt = (
            "You are an expert in logical reasoning. "
            "Your role is to explain logical arguments clearly and naturally, the way a knowledgeable human teacher would.\n\n"
            "IMPORTANT RULES:\n"
            "- Synthesize ideas across premises — show how they connect and combine.\n"
            "- Use transitional language: 'Since', 'Therefore', 'This means', 'Combined with', 'As a result', 'It follows that'.\n"
            "- Never just copy or list premises verbatim — interpret and derive.\n"
            "- Your explanation should read as a flowing argument, not a bullet list of facts."
        )

        return self._generate_text(system_prompt, user_prompt, max_new_tokens=512)

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

            user_prompt = (
                f"The following premises have been formally proven (via Z3 SMT solver) to entail the conclusion.\n\n"
                f"Key premises:\n"
                f"{core_premises_text}\n\n"
                f"Conclusion:\n"
                f"- {conclusion_nl}\n\n"
                f"{proof_skeleton_instruction}\n\n"
                f"Write a numbered step-by-step explanation that traces the logical chain from premises to conclusion. "
                f"Each step should build on the previous one and show a new deduction or inference — "
                f"NOT simply restate a premise. Use transitions like 'Since', 'Therefore', 'This means', 'It follows that'. "
                f"Format: 'Step N: <explanation>'."
            )
        elif result == sat:
            model_str = str(verification["model"])
            user_prompt = (
                f"The SMT solver found a counterexample: the premises are all TRUE yet the conclusion is FALSE.\n\n"
                f"Premises:\n"
                f"{chr(10).join(f'- {p}' for p in premises_nl)}\n\n"
                f"Conclusion being tested:\n"
                f"- {conclusion_nl}\n\n"
                f"Counterexample (Z3 model):\n"
                f"{model_str}\n\n"
                f"Explain in numbered steps why this counterexample breaks the conclusion. "
                f"Show what the counterexample reveals about the logical gap. "
                f"Each step should advance the argument — do not just restate facts. "
                f"Format: 'Step N: <explanation>'."
            )
        else:
            user_prompt = (
                f"The solver could not determine whether the conclusion is entailed by the premises.\n\n"
                f"Premises:\n"
                f"{chr(10).join(f'- {p}' for p in premises_nl)}\n\n"
                f"Conclusion:\n"
                f"- {conclusion_nl}\n\n"
                f"In numbered steps, analyse why the relationship is indeterminate. "
                f"What information is missing? What would need to be true for the conclusion to follow? "
                f"Each step should offer a new insight, not repeat a premise. "
                f"Format: 'Step N: <explanation>'."
            )

        system_prompt = (
            "You are an expert in logical reasoning. "
            "Your role is to explain arguments the way a knowledgeable human teacher would — "
            "through clear numbered steps that DERIVE new insights, not restate known facts.\n\n"
            "IMPORTANT RULES:\n"
            "- Each 'Step N:' must advance the reasoning chain with a new deduction or inference.\n"
            "- Synthesize across premises: show how they combine to produce a new conclusion.\n"
            "- Use transitional language: 'Since', 'Therefore', 'This means', 'Combined with', 'It follows that'.\n"
            "- Never copy a premise verbatim as a step — interpret and derive from it."
        )

        raw_text = self._generate_text(system_prompt, user_prompt, max_new_tokens=512)
        cot_steps = self._parse_cot_steps(raw_text)
        return raw_text, cot_steps
