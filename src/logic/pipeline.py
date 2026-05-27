import re
import z3
from src.logic.translation.pipeline import NLToFOLPipeline
from src.logic.reasoning.pipeline import ReasoningPipeline
from src.logic.reasoning.verifier import verify_with_z3
from src.llm import LLMClient
from src.llm.prompts import OPEN_ENDED_SYSTEM_PROMPT, OPEN_ENDED_USER_PROMPT_TEMPLATE


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


def detect_question_type(conclusion_nl: str) -> str:
    """Detect question type based on standard patterns."""
    options = parse_mcq_options(conclusion_nl)
    if len(options) >= 2:
        # Check for multiple-answer indicators in conclusion_nl
        text_lower = conclusion_nl.lower()
        mc_indicators = [
            "select all",
            "all that apply",
            "which of the following are",
            "choose all",
            "multiple answers",
            "multiple choices",
            "more than one",
            "all correct",
        ]
        if any(ind in text_lower for ind in mc_indicators):
            return "multiple_choice"
        return "single_choice"
    
    # Check for yes/no/uncertain questions
    text_stripped = conclusion_nl.strip()
    text_lower = text_stripped.lower()
    
    # If conclusion is a simple statement, it's boolean entailment, handled by yes_no flow
    if not text_stripped.endswith("?") and not any(text_lower.startswith(w) for w in ["who", "what", "which", "where", "when", "why", "how"]):
        return "yes_no"
        
    yes_no_starters = [
        "is", "are", "does", "do", "can", "will", "was", "were", "has", "have", "should", "would",
        "if", "whether", "is it true", "could"
    ]
    if any(text_lower.startswith(w) for w in yes_no_starters) or "yes or no" in text_lower:
        return "yes_no"
        
    # Check for open-ended queries (Who, What, Which, Where, When, Why, How)
    open_ended_starters = ["who", "what", "which", "where", "when", "why", "how"]
    if any(text_lower.startswith(w) for w in open_ended_starters) or "?" in text_stripped:
        return "open_ended"
        
    # Fallback to yes_no (boolean statement entailment)
    return "yes_no"


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

    def run_pipeline(self, premises_nl: list[str], conclusion_nl: str, question_type: str = None) -> dict:
        # Propagate models if loaded
        if self.translation_pipeline.model:
            self.reasoning_pipeline.tokenizer = self.translation_pipeline.tokenizer
            self.reasoning_pipeline.model = self.translation_pipeline.model

        # Auto-detect question type if not specified
        if not question_type or question_type == "auto":
            question_type = detect_question_type(conclusion_nl)

        # Detect multiple-choice options if MCQ type is selected or auto-detected
        options = parse_mcq_options(conclusion_nl)
        
        if question_type in ("single_choice", "multiple_choice") or (len(options) >= 2 and not question_type):
            # MCQ Flow
            opt_keys = sorted(options.keys())
            combined_nl = premises_nl + [options[k] for k in opt_keys]
            
            # Translate all together to ensure predicate alignment
            all_fol = self.translation_pipeline.translate_list(combined_nl)
            
            premises_fol = all_fol[:len(premises_nl)]
            options_fol = {}
            for idx, k in enumerate(opt_keys):
                offset = len(premises_nl) + idx
                options_fol[k] = all_fol[offset] if offset < len(all_fol) else ""

            # Filter premises to those most relevant to the question
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

            correct_options = []
            correct_verifications = []

            if question_type == "multiple_choice":
                # Multiple Choice: return ALL correct (entailed) options
                if unsat_candidates:
                    correct_options = [x[0] for x in unsat_candidates]
                    correct_verifications = [x[1] for x in unsat_candidates]
                elif consistent_candidates:
                    # Fallback to consistent options
                    correct_options = [x[0] for x in consistent_candidates]
                    correct_verifications = [x[1] for x in consistent_candidates]
                else:
                    # Fallback to the first option
                    correct_options = [opt_keys[0]] if opt_keys else []
                    correct_verifications = []
                    if correct_options:
                        opt_fol = options_fol.get(correct_options[0], "")
                        try:
                            ver = self.reasoning_pipeline.verify(filt_premises_fol, opt_fol, negate_conclusion=True)
                            correct_verifications.append(ver)
                        except Exception:
                            correct_verifications.append({"result": z3.unknown, "unsat_core": [], "model": None})
            else:
                # Single Choice: pick the best option
                if unsat_candidates:
                    # Pick the option whose proof uses the fewest premises (tightest entailment)
                    unsat_candidates.sort(key=lambda x: x[2])
                    correct_options = [unsat_candidates[0][0]]
                    correct_verifications = [unsat_candidates[0][1]]
                elif consistent_candidates:
                    # Process of Elimination
                    correct_options = [consistent_candidates[0][0]]
                    correct_verifications = [consistent_candidates[0][1]]
                else:
                    correct_options = [opt_keys[0]] if opt_keys else []
                    correct_verifications = []
                    if correct_options:
                        opt_fol = options_fol.get(correct_options[0], "")
                        try:
                            ver = self.reasoning_pipeline.verify(filt_premises_fol, opt_fol, negate_conclusion=True)
                            correct_verifications.append(ver)
                        except Exception:
                            correct_verifications.append({"result": z3.unknown, "unsat_core": [], "model": None})

            if not correct_options:
                correct_options = [opt_keys[0]] if opt_keys else [""]
                correct_verifications = [{"result": z3.unknown, "unsat_core": [], "model": None}]

            best_verification = correct_verifications[0]

            # Generate combined reasoning/CoT
            if len(correct_options) > 1:
                conclusion_nl_cot = " and ".join(f"Option {opt}: {options[opt]}" for opt in correct_options)
                # Create a combined verification structure
                merged_unsat_core = list(set().union(*(v.get("unsat_core", []) for v in correct_verifications)))
                # If all are unsat, result is unsat
                combined_result = z3.unsat if all(v.get("result") == z3.unsat for v in correct_verifications) else z3.sat
                combined_proof = "\n\n".join(f"Proof for Option {opt}:\n{v.get('proof')}" for opt, v in zip(correct_options, correct_verifications) if v.get("proof") is not None) or None
                combined_verification = {
                    "result": combined_result,
                    "unsat_core": merged_unsat_core,
                    "proof": combined_proof,
                    "model": best_verification.get("model")
                }
            else:
                conclusion_nl_cot = f"Option {correct_options[0]}: {options[correct_options[0]]}"
                combined_verification = best_verification

            reasoning, cot = self.generate_cot(
                premises_nl=filt_premises_nl,
                conclusion_nl=conclusion_nl_cot,
                verification=combined_verification
            )

            answer_val = correct_options if question_type == "multiple_choice" else correct_options[0]

            # For conclusion_fol, we can represent it as AND of the options if multiple, else single
            if len(correct_options) > 1:
                conclusion_fol_str = f"AND(" + ", ".join(options_fol.get(opt, "") for opt in correct_options) + ")"
            else:
                conclusion_fol_str = options_fol.get(correct_options[0], "")

            return {
                "answer": answer_val,
                "confidence": _compute_confidence(best_verification, total_premises=len(filt_premises_fol)),
                "premises_fol": filt_premises_fol,
                "conclusion_fol": conclusion_fol_str,
                "verification": combined_verification,
                "reasoning": reasoning,
                "cot": cot,
            }

        elif question_type == "open_ended":
            # Open-Ended Flow: Generate candidate answer using LLM, then verify
            premises_text = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(premises_nl))
            user_prompt = OPEN_ENDED_USER_PROMPT_TEMPLATE.format(
                premises_text=premises_text,
                question_nl=conclusion_nl
            )
            candidate_answer = self.llm_client.generate_text(
                prompt=user_prompt,
                system_prompt=OPEN_ENDED_SYSTEM_PROMPT,
                max_new_tokens=256
            ).strip()

            # Translate the premises and the generated candidate answer statement
            premises_fol, conclusion_fol = self.translate_premises_and_conclusion(premises_nl, candidate_answer)

            # Filter premises to those most relevant
            filt_premises_nl, filt_premises_fol, _ = self.reasoning_pipeline.filter_relevant_premises(
                premises_nl, candidate_answer, premises_fol
            )

            # Verify entailment of candidate answer with Z3
            verification = self.reasoning_pipeline.verify(filt_premises_fol, conclusion_fol, negate_conclusion=True)
            
            # Check if the generated answer is confirmed by Z3
            if verification["result"] == z3.unsat:
                answer_status = candidate_answer
            else:
                # If Z3 cannot confirm, see if we can disprove it
                try:
                    verification_neg = self.reasoning_pipeline.verify(filt_premises_fol, conclusion_fol, negate_conclusion=False)
                    if verification_neg["result"] == z3.unsat:
                        # Contradicts!
                        verification = verification_neg
                        candidate_answer = f"NOT ({candidate_answer})"
                        conclusion_fol = f"NOT ({conclusion_fol})"
                except Exception:
                    pass
                answer_status = candidate_answer # Keep candidate but it's not entailed (lower confidence)

            reasoning, cot = self.generate_cot(filt_premises_nl, candidate_answer, verification)

            return {
                "answer": answer_status,
                "confidence": _compute_confidence(verification, total_premises=len(filt_premises_fol)),
                "premises_fol": filt_premises_fol,
                "conclusion_fol": conclusion_fol,
                "verification": verification,
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

