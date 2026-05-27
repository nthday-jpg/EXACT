import re
import z3
from src.logic.translation.pipeline import NLToFOLPipeline
from src.logic.reasoning.pipeline import ReasoningPipeline
from src.logic.reasoning.verifier import verify_with_z3
from src.llm import LLMClient

def parse_mcq_options(text: str) -> dict[str, str]:
    """Parse options A, B, C, D from the text if present."""
    options = {}
    pattern = r'(?:\s+|^)([A-D])[\.\)]\s+(.*?)(?=\s+[A-D][\.\)]\s+|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    for opt_char, opt_text in matches:
        options[opt_char] = opt_text.strip()
    return options


def _compute_confidence(verification: dict, total_premises: int = 0) -> float:
    """Compute a confidence score (0.0–1.0) based on the Z3 verification result.

    Scoring rationale:
    - unsat: conclusion is formally proven; score scales with proof tightness.
        A smaller unsat core relative to total premises means a tighter, more
        focused proof → higher confidence (range 0.75–1.00).
    - sat: a counterexample was found; the answer is definitively not entailed.
        We are fairly confident in the "No/wrong option" judgment → 0.60.
    - unknown: Z3 could not decide; we have low confidence → 0.30.
    """
    result = verification.get("result")
    if result == z3.unsat:
        core_size = len(verification.get("unsat_core", []))
        # Tightness: 1.0 when core has 1 element, approaches 0 as core → total
        denom = max(total_premises, core_size, 1)
        tightness = 1.0 - (core_size - 1) / denom
        # Map tightness to [0.75, 1.00]
        return round(0.75 + tightness * 0.25, 4)
    if result == z3.sat:
        return 0.60
    return 0.30

class LogicalReasoningPipeline:
    """
    Backward-compatible wrapper for the End-to-End Logical Reasoning Pipeline.
    Delegates to the modular NLToFOLPipeline for translation and ReasoningPipeline for Z3 reasoning.
    """
    def __init__(self, use_local: bool = True, model_dir: str = None, llm_client = None):
        self.use_local = use_local
        self.model_dir = model_dir
        
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(use_local=use_local, model_dir=model_dir)
            
        self.translation_pipeline = NLToFOLPipeline(use_local=use_local, model_dir=model_dir, llm_client=self.llm_client)
        self.reasoning_pipeline = ReasoningPipeline(use_local=use_local, model_dir=model_dir, llm_client=self.llm_client)


    @property
    def tokenizer(self):
        return self.translation_pipeline.tokenizer or self.reasoning_pipeline.tokenizer

    @property
    def model(self):
        return self.translation_pipeline.model or self.reasoning_pipeline.model

    @property
    def device(self):
        return self.translation_pipeline.device

    def load_local_model(self):
        self.translation_pipeline.load_local_model()
        self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
        self.reasoning_pipeline.model = self.translation_pipeline.model

    def translate_premises_and_conclusion(self, premises_nl: list[str], conclusion_nl: str) -> tuple[list[str], str]:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        return self.translation_pipeline.translate_premises_and_conclusion(premises_nl, conclusion_nl)

    def verify_with_z3(self, premises_fol: list[str], conclusion_fol: str, negate_conclusion: bool = True) -> dict:
        return self.reasoning_pipeline.verify(premises_fol, conclusion_fol, negate_conclusion=negate_conclusion)

    def generate_reasoning(self, premises_nl: list[str], conclusion_nl: str, verification: dict) -> str:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        return self.reasoning_pipeline.generate_reasoning(premises_nl, conclusion_nl, verification)

    def generate_cot(
        self, premises_nl: list[str], conclusion_nl: str, verification: dict
    ) -> tuple[str, list[str]]:
        """Generate structured CoT reasoning. Returns (reasoning_str, cot_steps)."""
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model
        return self.reasoning_pipeline.generate_cot(premises_nl, conclusion_nl, verification)

    def run_pipeline(self, premises_nl: list[str], conclusion_nl: str) -> dict:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model

        # Detect multiple-choice question
        options = parse_mcq_options(conclusion_nl)
        if len(options) >= 2:
            # MCQ Flow: Find correct option and generate UNSAT reasoning for it
            opt_keys = sorted(options.keys())
            combined_nl = premises_nl + [options[k] for k in opt_keys]
            
            # Translate all together to ensure predicate alignment
            all_fol = self.translation_pipeline.translate_list(combined_nl)
            
            premises_fol = all_fol[:len(premises_nl)]
            options_fol = {}
            for idx, k in enumerate(opt_keys):
                offset = len(premises_nl) + idx
                options_fol[k] = all_fol[offset] if offset < len(all_fol) else ""

            # Filter premises to those most relevant to the question (uses full question as context)
            filt_premises_nl, filt_premises_fol, _ = self.reasoning_pipeline.filter_relevant_premises(
                premises_nl, conclusion_nl, premises_fol
            )

            # Evaluate ALL options
            unsat_candidates: list[tuple[str, dict, int]] = []  # (key, verification, core_size)
            consistent_candidates: list[tuple[str, dict]] = []  # (key, verification)

            for k in opt_keys:
                opt_fol = options_fol.get(k, "")
                if not opt_fol:
                    continue
                try:
                    # 1. Check if the option is entailed (negate_conclusion=True)
                    verification = self.reasoning_pipeline.verify(filt_premises_fol, opt_fol, negate_conclusion=True)
                    if verification.get("result") == z3.unsat:
                        core_size = len(verification.get("unsat_core", []))
                        unsat_candidates.append((k, verification, core_size))
                    elif verification.get("result") == z3.sat:
                        # 2. Check if the option contradicts the premises (negate_conclusion=False)
                        verif_contra = self.reasoning_pipeline.verify(filt_premises_fol, opt_fol, negate_conclusion=False)
                        if verif_contra.get("result") != z3.unsat:
                            # It is consistent!
                            consistent_candidates.append((k, verification))
                except Exception:
                    pass

            correct_option = None
            correct_verification = None

            if unsat_candidates:
                # Pick the option whose proof uses the fewest premises (tightest entailment)
                unsat_candidates.sort(key=lambda x: x[2])
                correct_option, correct_verification, _ = unsat_candidates[0]
            elif consistent_candidates:
                # Process of Elimination: Pick the first consistent (non-contradictory) option
                correct_option, correct_verification = consistent_candidates[0]

            if not correct_option and opt_keys:
                # Fallback to the first option
                correct_option = opt_keys[0]
                opt_fol = options_fol.get(correct_option, "")
                try:
                    correct_verification = self.reasoning_pipeline.verify(filt_premises_fol, opt_fol, negate_conclusion=True)
                except Exception:
                    correct_verification = {"result": z3.unknown, "unsat_core": [], "model": None}

            reasoning, cot = self.generate_cot(
                premises_nl=filt_premises_nl,
                conclusion_nl=f"Option {correct_option}: {options[correct_option]}",
                verification=correct_verification
            )

            return {
                "answer": correct_option,
                "confidence": _compute_confidence(correct_verification, total_premises=len(filt_premises_fol)),
                "premises_fol": filt_premises_fol,
                "conclusion_fol": options_fol.get(correct_option, ""),
                "verification": correct_verification,
                "reasoning": reasoning,
                "cot": cot,
            }
        else:
            # Yes/No or Statement Flow: Dual satisfiability check (both entailed or negated entailed)
            premises_fol, conclusion_fol = self.translate_premises_and_conclusion(premises_nl, conclusion_nl)

            # Filter premises to those most relevant to the conclusion
            filt_premises_nl, filt_premises_fol, _ = self.reasoning_pipeline.filter_relevant_premises(
                premises_nl, conclusion_nl, premises_fol
            )

            # Check if conclusion is entailed
            verification = self.reasoning_pipeline.verify(filt_premises_fol, conclusion_fol, negate_conclusion=True)
            answer = "Uncertain"

            if verification["result"] == z3.unsat:
                # Conclusion is logically entailed
                answer = "Yes"
            else:
                # Check if negation of conclusion is entailed
                try:
                    verification_neg = self.reasoning_pipeline.verify(filt_premises_fol, conclusion_fol, negate_conclusion=False)
                    if verification_neg["result"] == z3.unsat:
                        verification = verification_neg
                        conclusion_nl = f"NOT ({conclusion_nl})"
                        conclusion_fol = f"NOT ({conclusion_fol})"
                        answer = "No"
                except Exception:
                    pass

            reasoning, cot = self.generate_cot(filt_premises_nl, conclusion_nl, verification)

            return {
                "answer": answer,
                "confidence": _compute_confidence(verification, total_premises=len(filt_premises_fol)),
                "premises_fol": filt_premises_fol,
                "conclusion_fol": conclusion_fol,
                "verification": verification,
                "reasoning": reasoning,
                "cot": cot,
            }
