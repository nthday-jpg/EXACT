import sys
import unittest
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Enable Z3 proof globally
import z3
z3.set_param('proof', True)

from src.logic.pipeline import LogicalReasoningPipeline, detect_question_type


class MockLLMClient:
    """Mock LLM client to simulate translation, reasoning, and open-ended answers."""
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        self.system_prompt = ""
        self.temperature = 0.0

    def generate_text(self, prompt: str, system_prompt: str = None, max_new_tokens: int = 512) -> str:
        prompt_lower = prompt.lower()
        
        # Check for Unknown fallbacks first
        if "insufficient information" in prompt_lower or (system_prompt and "or 'unknown'" in system_prompt.lower()):
            return "Unknown"

        # 1. Open-ended question candidate generation
        if "concise answer statement:" in prompt_lower:
            if "who is mortal" in prompt_lower:
                return "Socrates is mortal."
            if "what is john's arrival time" in prompt_lower:
                return "john arrival time is Time800AM"
            return "Unknown answer."

        # 1b. Combined Glossary + Translation
        if "generate a unified glossary, and translate them" in prompt_lower:
            if "socrates is a human" in prompt_lower or "every human is mortal" in prompt_lower:
                return """
                {
                  "predicates": {
                    "Human(x)": "x is a human",
                    "Mortal(x)": "x is mortal",
                    "qualifies(x)": "x qualifies"
                  },
                  "constants": {
                    "Socrates": "Socrates",
                    "John": "John",
                    "Time800AM": "Time800AM"
                  },
                  "formulas": ["Human(Socrates)", "ForAll(x, Human(x) -> Mortal(x))", "Mortal(Socrates)", "Human(Socrates)", "Mortal(Socrates)", "Mortal(John)", "Mortal(Socrates)", "Mortal(John)"]
                }
                """
            if "socrates is mortal" in prompt_lower:
                return '{"formulas": ["Mortal(Socrates)"]}'
            if "john is a driver" in prompt_lower:
                return '{"formulas": ["Driver(John)"]}'
            if "john qualifies" in prompt_lower:
                return '{"formulas": ["qualifies(John)"]}'
            return '{"formulas": ["P(x)"]}'
            
        # 2. Glossary generation (Stage 1 translation)
        if "generate the strict json glossary" in prompt_lower:
            return """
            {
              "predicates": {
                "Human(x)": "x is a human",
                "Mortal(x)": "x is mortal",
                "qualifies(x)": "x qualifies"
              },
              "constants": {
                "Socrates": "Socrates",
                "John": "John",
                "Time800AM": "Time800AM"
              }
            }
            """

        # 3. Translate to FOL (Stage 2 translation / Fallback)
        if "convert the following premises into canonical first-order logic" in prompt_lower or "first-order logic formulas" in prompt_lower:
            # Map specific sentences to FOL
            if "socrates is a human" in prompt_lower or "every human is mortal" in prompt_lower:
                # Return standard list of FOLs
                return '["Human(Socrates)", "ForAll(x, Human(x) -> Mortal(x))", "Mortal(Socrates)", "Human(Socrates)", "Mortal(Socrates)", "Mortal(John)", "Mortal(Socrates)", "Mortal(John)"]'
            if "socrates is mortal" in prompt_lower:
                return '["Mortal(Socrates)"]'
            if "john is a driver" in prompt_lower:
                return '["Driver(John)"]'
            if "john qualifies" in prompt_lower:
                return '["qualifies(John)"]'
            return '["P(x)"]'

        # 4. Premise filtering
        if "select at most" in prompt_lower:
            return "[1, 2]"

        # 5. CoT explanation generation
        if "step n: <explanation>" in prompt_lower or "numbered step-by-step" in prompt_lower:
            return "Step 1: Socrates is a human.\nStep 2: Since every human is mortal, Socrates is mortal."

        # 6. Flowing reasoning generation
        return "Because Socrates is a human and all humans are mortal, Socrates must be mortal."


class TestQuestionTypes(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockLLMClient()
        self.pipeline = LogicalReasoningPipeline(use_local=False, llm_client=self.mock_client)

    def test_question_type_detection(self):
        # MCQ (Single)
        mcq_single = "Which option is correct?\nA. Socrates is mortal\nB. Socrates is human"
        self.assertEqual(detect_question_type(mcq_single), "single_choice")

        # MCQ (Multiple)
        mcq_multiple = "Select all that apply:\nA. Socrates is mortal\nB. Socrates is human"
        self.assertEqual(detect_question_type(mcq_multiple), "multiple_choice")

        # Yes/No Question
        yes_no_q = "Is Socrates mortal?"
        self.assertEqual(detect_question_type(yes_no_q), "yes_no")

        # Yes/No Statement
        yes_no_stmt = "Socrates is mortal."
        self.assertEqual(detect_question_type(yes_no_stmt), "yes_no")

        # Open-ended
        open_ended_who = "Who is mortal?"
        self.assertEqual(detect_question_type(open_ended_who), "open_ended")

        open_ended_what = "What is John's arrival time?"
        self.assertEqual(detect_question_type(open_ended_what), "open_ended")

    def test_single_choice_pipeline(self):
        # Premises and single-choice question
        premises = [
            "Every human is mortal.",
            "Socrates is a human."
        ]
        conclusion = (
            "Which of the following is true?\n"
            "A. Socrates is a driver\n"
            "B. Socrates is mortal\n"
            "C. John qualifies\n"
            "D. None of the above"
        )
        
        # Override translator return to return Option B's FOL as entailed, and others as not entailed
        # options are: ['A. Socrates is a driver', 'B. Socrates is mortal', 'C. John qualifies', 'D. None of the above']
        # We want FOL of B: "Mortal(Socrates)" to be entailed
        def custom_translate_list(nl_list):
            return [
                "ForAll(x, Human(x) -> Mortal(x))", # Premise 1
                "Human(Socrates)",                  # Premise 2
                "Driver(Socrates)",                 # Option A (not entailed)
                "Mortal(Socrates)",                 # Option B (entailed!)
                "qualifies(John)",                  # Option C (not entailed)
                "NoneOfTheAbove"                    # Option D
            ]
        self.pipeline.translation_pipeline.translate_list = custom_translate_list

        result = self.pipeline.run_pipeline(premises, conclusion, question_type="single_choice")
        
        self.assertEqual(result["answer"], "B")
        self.assertGreaterEqual(result["confidence"], 0.75)
        self.assertEqual(result["conclusion_fol"], "Mortal(Socrates)")
        self.assertIn("Step 1", result["reasoning"] or result["cot"][0])

    def test_multiple_choice_pipeline(self):
        premises = [
            "Every human is mortal.",
            "Socrates is a human.",
            "John is a human."
        ]
        conclusion = (
            "Select all correct options:\n"
            "A. Socrates is mortal\n"
            "B. Socrates is a driver\n"
            "C. John is mortal\n"
            "D. None of the above"
        )

        def custom_translate_list(nl_list):
            return [
                "ForAll(x, Human(x) -> Mortal(x))", # Premise 1
                "Human(Socrates)",                  # Premise 2
                "Human(John)",                      # Premise 3
                "Mortal(Socrates)",                 # Option A (entailed!)
                "Driver(Socrates)",                 # Option B (not entailed)
                "Mortal(John)",                     # Option C (entailed!)
                "NoneOfTheAbove"                    # Option D
            ]
        self.pipeline.translation_pipeline.translate_list = custom_translate_list

        result = self.pipeline.run_pipeline(premises, conclusion, question_type="multiple_choice")
        
        # Should return both A and C
        self.assertEqual(result["answer"], ["A", "C"])
        self.assertIn("AND(Mortal(Socrates), Mortal(John))", result["conclusion_fol"])
        self.assertEqual(result["verification"]["result"], z3.unsat)

    def test_yes_no_uncertain_pipeline(self):
        premises = [
            "Every human is mortal.",
            "Socrates is a human."
        ]
        
        # Test "Yes" case
        def custom_translate_yes(premises_nl, conclusion_nl):
            return (
                ["ForAll(x, Human(x) -> Mortal(x))", "Human(Socrates)"],
                "Mortal(Socrates)"
            )
        self.pipeline.translate_premises_and_conclusion = custom_translate_yes
        
        result_yes = self.pipeline.run_pipeline(premises, "Is Socrates mortal?", question_type="yes_no")
        self.assertEqual(result_yes["answer"], "Yes")
        self.assertGreaterEqual(result_yes["confidence"], 0.75)

        # Test "No" case (Contradiction)
        # Z3 will check conclusion (which fails) and negation NOT(conclusion) which succeeds
        def custom_translate_no(premises_nl, conclusion_nl):
            return (
                ["ForAll(x, Human(x) -> Mortal(x))", "Human(Socrates)"],
                "NOT (Mortal(Socrates))" # Negation of the query
            )
        self.pipeline.translate_premises_and_conclusion = custom_translate_no
        
        result_no = self.pipeline.run_pipeline(premises, "Is Socrates immortal?", question_type="yes_no")
        self.assertEqual(result_no["answer"], "No")
        self.assertGreaterEqual(result_no["confidence"], 0.75)

    def test_open_ended_pipeline(self):
        premises = [
            "Every human is mortal.",
            "Socrates is a human."
        ]
        
        # Custom translator to return Socrates is mortal as conclusion FOL
        def custom_translate(premises_nl, conclusion_nl):
            return (
                ["ForAll(x, Human(x) -> Mortal(x))", "Human(Socrates)"],
                "Mortal(Socrates)"
            )
        self.pipeline.translate_premises_and_conclusion = custom_translate
        
        result = self.pipeline.run_pipeline(premises, "Who is mortal?", question_type="open_ended")
        
        # The answer should be the candidate statement generated by mock client
        self.assertEqual(result["answer"], "Socrates is mortal.")
        self.assertEqual(result["conclusion_fol"], "Mortal(Socrates)")
        self.assertEqual(result["verification"]["result"], z3.unsat)
        self.assertGreaterEqual(result["confidence"], 0.75)

    def test_unknown_fallbacks(self):
        premises = [
            "Every human is mortal.",
            "Socrates is a human."
        ]
        
        # Scenario 1: Open-ended not entailed -> should automatically return "Unknown"
        def custom_translate_unprovable(premises_nl, conclusion_nl):
            return (
                ["ForAll(x, Human(x) -> Mortal(x))", "Human(Socrates)"],
                "Mortal(Plato)" # Plato is unprovable
            )
        self.pipeline.translate_premises_and_conclusion = custom_translate_unprovable
        
        result_oe = self.pipeline.run_pipeline(premises, "Who is mortal?", question_type="open_ended")
        self.assertEqual(result_oe["answer"], "Unknown")
        self.assertEqual(result_oe["confidence"], 0.60) # sat/not entailed has confidence 0.60
        
        # Scenario 2: Single Choice not entailed -> fallback to semantic "Unknown"
        # Mock translator to return empty list or empty strings for options
        def custom_translate_empty_options(nl_list):
            return [""] * len(nl_list)
        self.pipeline.translation_pipeline.translate_list = custom_translate_empty_options
        
        mcq_question = (
            "Which option is correct?\n"
            "A. Plato is mortal\n"
            "B. Socrates is a driver\n"
            "C. None of the above\n"
            "D. Something else"
        )
        result_mcq = self.pipeline.run_pipeline(premises, mcq_question, question_type="single_choice")
        self.assertEqual(result_mcq["answer"], "Unknown")
        self.assertEqual(result_mcq["confidence"], 0.30) # unknown verifications have confidence 0.30


if __name__ == "__main__":
    unittest.main()
