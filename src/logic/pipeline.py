import re
import z3
from src.logic.translation.pipeline import NLToFOLPipeline
from src.logic.reasoning.pipeline import ReasoningPipeline
from src.logic.reasoning.verifier import verify_with_z3

def parse_mcq_options(text: str) -> dict[str, str]:
    """Parse options A, B, C, D from the text if present."""
    options = {}
    pattern = r'(?:\s+|^)([A-D])[\.\)]\s+(.*?)(?=\s+[A-D][\.\)]\s+|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    for opt_char, opt_text in matches:
        options[opt_char] = opt_text.strip()
    return options

class LogicalReasoningPipeline:
    """
    Backward-compatible wrapper for the End-to-End Logical Reasoning Pipeline.
    Delegates to the modular NLToFOLPipeline for translation and ReasoningPipeline for Z3 reasoning.
    """
    def __init__(self, use_local: bool = True, model_dir: str = None, llm_client = None):
        self.use_local = use_local
        self.model_dir = model_dir
        self.llm_client = llm_client
        
        self.translation_pipeline = NLToFOLPipeline(use_local=use_local, model_dir=model_dir, llm_client=llm_client)
        self.reasoning_pipeline = ReasoningPipeline(use_local=use_local, model_dir=model_dir, llm_client=llm_client)

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
                
            correct_option = None
            correct_verification = None
            
            for k in opt_keys:
                opt_fol = options_fol.get(k, "")
                if not opt_fol:
                    continue
                try:
                    verification = self.reasoning_pipeline.verify(premises_fol, opt_fol, negate_conclusion=True)
                    if verification["result"] == z3.unsat:
                        correct_option = k
                        correct_verification = verification
                        break
                except Exception:
                    pass
            
            if not correct_option and opt_keys:
                correct_option = opt_keys[0]
                opt_fol = options_fol.get(correct_option, "")
                correct_verification = self.reasoning_pipeline.verify(premises_fol, opt_fol, negate_conclusion=True)
                
            reasoning = self.generate_reasoning(
                premises_nl=premises_nl,
                conclusion_nl=f"Option {correct_option}: {options[correct_option]}",
                verification=correct_verification
            )
            
            return {
                "premises_fol": premises_fol,
                "conclusion_fol": options_fol.get(correct_option, ""),
                "verification": correct_verification,
                "reasoning": reasoning
            }
        else:
            # Yes/No or Statement Flow: Dual satisfiability check (both entailed or negated entailed)
            premises_fol, conclusion_fol = self.translate_premises_and_conclusion(premises_nl, conclusion_nl)
            
            # Check if conclusion is entailed
            verification = self.reasoning_pipeline.verify(premises_fol, conclusion_fol, negate_conclusion=True)
            
            if verification["result"] != z3.unsat:
                # Check if negation of conclusion is entailed
                try:
                    verification_neg = self.reasoning_pipeline.verify(premises_fol, conclusion_fol, negate_conclusion=False)
                    if verification_neg["result"] == z3.unsat:
                        verification = verification_neg
                        conclusion_nl = f"NOT ({conclusion_nl})"
                        conclusion_fol = f"NOT ({conclusion_fol})"
                except Exception:
                    pass
                    
            reasoning = self.generate_reasoning(premises_nl, conclusion_nl, verification)
            
            return {
                "premises_fol": premises_fol,
                "conclusion_fol": conclusion_fol,
                "verification": verification,
                "reasoning": reasoning
            }
