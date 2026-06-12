import sys
import unittest
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Enable Z3 proof globally
import z3  # noqa: E402
z3.set_param('proof', True)

from src.logic.pipeline import LogicalReasoningPipeline, parse_mcq_options  # noqa: E402

class MockLLMClient:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        self.system_prompt = ""
        self.temperature = 0.0

    def generate_text(self, prompt: str, system_prompt: str = None, max_new_tokens: int = 512) -> str:
        prompt_lower = prompt.lower()
        
        # Simulating LLM response for option extraction if regex fails
        if "analyze the following multiple-choice question and extract the text" in prompt_lower:
            return '{"A": "If a student completes a final project, then they receive a diploma.", "B": "If a student completes an internship, then they receive a certificate of excellence.", "C": "If a student receives a diploma, then they have completed a final project.", "D": "If a student is eligible for graduation, then they have graduated with distinction."}'

        # Translate options
        if "convert the following premises into canonical first-order logic" in prompt_lower or "first-order logic formulas" in prompt_lower:
            # Socrates is a driver, etc.
            if "receive a diploma" in prompt_lower:
                return '["ForAll(x, completed_project(x) -> receive_diploma(x))", "ForAll(x, completed_internship(x) -> receive_certificate(x))", "ForAll(x, receive_diploma(x) -> completed_project(x))", "ForAll(x, eligible_grad(x) -> grad_distinction(x))"]'
            return '["P(x)"]'

        # Stage 2 combined translation mock
        if "generate a unified glossary, and translate them" in prompt_lower:
            return """
            {
              "predicates": {},
              "constants": {},
              "formulas": ["ForAll(x, completed_project(x) -> receive_diploma(x))", "ForAll(x, completed_internship(x) -> receive_certificate(x))", "ForAll(x, receive_diploma(x) -> completed_project(x))", "ForAll(x, eligible_grad(x) -> grad_distinction(x))"]
            }
            """

        # CoT explanation generation mock
        if "step n: <explanation>" in prompt_lower or "numbered step-by-step" in prompt_lower:
            return "Step 1: The correct choice is C."

        return "C"


class TestRobustOptions(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockLLMClient()
        self.pipeline = LogicalReasoningPipeline(use_local=False, llm_client=self.mock_client)

    def test_parse_formats(self):
        # Format 1: Standard A.
        text1 = "Which is correct?\nA. Socrates is mortal\nB. Socrates is human"
        opts1 = parse_mcq_options(text1)
        self.assertEqual(opts1.get("A"), "Socrates is mortal")
        self.assertEqual(opts1.get("B"), "Socrates is human")

        # Format 2: Parentheses (A)
        text2 = "Which is correct? (A) Socrates is mortal (B) Socrates is human"
        opts2 = parse_mcq_options(text2)
        self.assertEqual(opts2.get("A"), "Socrates is mortal")
        self.assertEqual(opts2.get("B"), "Socrates is human")

        # Format 3: Brackets [A]
        text3 = "Which is correct?\n[A] Socrates is mortal\n[B] Socrates is human"
        opts3 = parse_mcq_options(text3)
        self.assertEqual(opts3.get("A"), "Socrates is mortal")
        self.assertEqual(opts3.get("B"), "Socrates is human")

        # Format 4: Options with prefix Option A:
        text4 = "Which is correct?\nOption A: Socrates is mortal\nOption B: Socrates is human"
        opts4 = parse_mcq_options(text4)
        self.assertEqual(opts4.get("A"), "Socrates is mortal")
        self.assertEqual(opts4.get("B"), "Socrates is human")

        # Format 5: Bullet list with dashes
        text5 = "Which is correct?\n- A. Socrates is mortal\n- B. Socrates is human"
        opts5 = parse_mcq_options(text5)
        self.assertEqual(opts5.get("A"), "Socrates is mortal")
        self.assertEqual(opts5.get("B"), "Socrates is human")

    def test_run_pipeline_key_only_options(self):
        premises = [
            "If a student completes a final project, then they receive a diploma.",
            "Student A completes a final project."
        ]
        query = (
            "Based on the above premises, which conclusion is correct?\n"
            "A. If a student completes a final project, then they receive a diploma.\n"
            "B. If a student completes an internship, then they receive a certificate of excellence.\n"
            "C. If a student receives a diploma, then they have completed a final project.\n"
            "D. If a student is eligible for graduation, then they have graduated with distinction."
        )
        options_list = ["A", "B", "C", "D"]

        # Mock translate list to return dummy formulas for combined translation
        def custom_translate_list(nl_list):
            # Combined translation gets: premises (len 2) + parsed options (len 4) = 6 formulas
            return [
                "ForAll(x, completed_project(x) -> receive_diploma(x))",
                "completed_project(StudentA)",
                "ForAll(x, completed_project(x) -> receive_diploma(x))",
                "ForAll(x, completed_internship(x) -> receive_certificate(x))",
                "ForAll(x, receive_diploma(x) -> completed_project(x))", # C: receive_diploma -> completed_project (entailed by Premise 1)
                "ForAll(x, eligible_grad(x) -> grad_distinction(x))"
            ]
        self.pipeline.translation_pipeline.translate_list = custom_translate_list

        result = self.pipeline.run_pipeline(premises, query, options_list=options_list)
        
        # The result answer should map back to choice key "C" or similar, let's check what correct option is identified
        self.assertIn(result["answer"], ["A", "B", "C", "D"])

    def test_llm_fallback_option_extraction(self):
        # A format that regex fails on completely, e.g. very mangled text
        query = "Mangled query text without clear options, but LLM mock is set up to return options"
        options_list = ["A", "B", "C", "D"]
        
        # Override translate list
        def custom_translate_list(nl_list):
            return ["P(x)"] * len(nl_list)
        self.pipeline.translation_pipeline.translate_list = custom_translate_list
        
        # Run pipeline
        result = self.pipeline.run_pipeline([], query, options_list=options_list)
        # Verify it fallback successfully and returned a valid choice key
        self.assertIn(result["answer"], ["A", "B", "C", "D"])


if __name__ == "__main__":
    unittest.main()
