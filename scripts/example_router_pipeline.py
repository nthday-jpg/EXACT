"""
Example: Using the Physics Router Pipeline

This demonstrates the complete flow from question to answer:
1. Question → Router (LLM classification)
2. Classification → Reasoning Polices Assembly (domains + type)
3. Reasoning Policies → Full Prompt (with reasoning policies + few-shots)
4. Solver → Answer (with structured JSON output)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from src.physics.api import run_physics
from src.physics.types import PhysicsTask
from src.physics.router import QuestionClassification, classify_question
from src.physics.registry import get_solver_prompt


def example_router():
    """Example 1: Classify a question."""
    load_dotenv()
    question = """
    Two point charges, q1 = 4e-6 C and q2 = -6.4e-6 C, are placed at points A and B, 
    separated by 0.2 m in air. Determine the magnitude of the electric force acting 
    on q3 = -5e-8 C placed at point C, given that AC = 0.12 m and BC = 0.16 m.
    """
    
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        print("[physics-router] HF_API_KEY not set; router calls may fail.", file=sys.stderr)
    default_model = os.getenv("DEFAULT_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    router_model_env = os.getenv("ROUTER_MODEL")
    model_name = router_model_env or default_model
    if not router_model_env:
        print(f"[physics-router] ROUTER_MODEL not set; using DEFAULT_MODEL={default_model}.", file=sys.stderr)
    
    # Classify the question
    classification = classify_question(
        question,
        model_name=model_name,
        api_key=api_key,
    )
    
    print("=== Router Output ===")
    print(f"Domains: {classification.domains}")
    print(f"Question Type: {classification.question_type}")


def example_policies_assembly():
    """Example 2: Assemble policiess for selected domains."""
    domains = ["electrostatic_field", "coordinate_geometry"]
    question_type = "Numerical"
    
    classification = QuestionClassification(domains, question_type)
    solver_prompt = get_solver_prompt(classification)
    
    print("=== Assembled Reasoning Polices Prompt ===")
    print(solver_prompt[:500])  # First 500 chars
    print("\n... [truncated] ...")


async def example_full_pipeline() -> None:
    """Example 3: Full pipeline with routed execution."""
    load_dotenv()
    api_key = os.getenv("HF_API_KEY")
    if not api_key:
        print("[physics-router] HF_API_KEY not set; model calls may fail.", file=sys.stderr)
    default_model = os.getenv("DEFAULT_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    physics_model_env = os.getenv("PHYSICS_MODEL")
    model_name = physics_model_env or default_model
    if not physics_model_env:
        print(f"[physics-router] PHYSICS_MODEL not set; using DEFAULT_MODEL={default_model}.", file=sys.stderr)
    router_model_env = os.getenv("ROUTER_MODEL")
    router_model = router_model_env or default_model
    if not router_model_env:
        print(f"[physics-router] ROUTER_MODEL not set; using DEFAULT_MODEL={default_model}.", file=sys.stderr)
    task = PhysicsTask(
        question="Two point charges, q1 = 4e-6 C and q2 = -6.4e-6 C, are placed at points A and B, separated by 0.2 m in air. Determine the magnitude of the electric force acting on q3 = -5e-8 C placed at point C, given that AC = 0.12 m and BC = 0.16 m.",
        correct={"ans": [0.1642], "unit": ["N"]},  # Example correct answer
    )
    
    # Run with router
    result = await run_physics(
        task,
        model_name=model_name,
        api_key=api_key,
        router_model_name=router_model,
        output_path="runs/results.json",
    )
    
    print("=== Full Pipeline Results ===")
    print(f"Question: {result.result.task.question[:100]}...")
    print(f"Correct: {result.result.task.correct}")
    print(f"Model Answer: {result.result.model_answer}")
    print(f"Is Correct: {result.is_correct}")
    print(f"Reason: {result.reason}")
    print()


if __name__ == "__main__":
    print("Physics Router Pipeline Examples\n")
    
    print("1. ROUTER CLASSIFICATION")
    print("-" * 50)
    example_router()
    
    print("\n2. policies ASSEMBLY")
    print("-" * 50)
    example_policies_assembly()
    
    print("\n3. FULL PIPELINE EXECUTION")
    print("-" * 50)
    asyncio.run(example_full_pipeline())
