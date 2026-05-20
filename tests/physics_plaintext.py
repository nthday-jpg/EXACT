from src.llm.llm_client import LLMClient
from dotenv import load_dotenv
import os
import pandas as pd
import json

def main():
    load_dotenv()
    api_key = os.getenv("HF_API_KEY")
    model = "Qwen/Qwen3-8B:featherless-ai"
    instructions = "You are a physics expert. " \
    "Answer questions in json format with the following keys: " \
    "- explanation: Step by step explanation of the answer. " \
    "- answer: The final answer, a number. " \
    "- unit: The unit of the answer. " 

    #randomly sample 20 questions from the physics dataset, store questions and correct answers and model answers, explanations in a json file
    df = pd.read_csv("data/physics.csv")
    sampled_df = df.sample(n=20, random_state=42)

    llm_client = LLMClient(
        model_name=model,
        api_key=api_key,
        system_prompt=instructions
    )

    results = []
    for i, row in sampled_df.iterrows():
        print(f"Processing question {i+1}/20")
        question = row["question"]
        correct_answer = row["answer"]
        correct_units = row["unit"]

        response = llm_client.generate(question)
        response = json.loads(response)  # Assuming the model returns a JSON string
        results.append({
            "question": question,
            "correct_answer": correct_answer,
            "correct_units": correct_units,
            "model_answer": response["answer"],
            "model_explanation": response["explanation"],
            "model_units": response["unit"],
            "correct_units": correct_units
        })
    correct_count = sum(1 for r in results if r["model_answer"] == r["correct_answer"])

    # Save results to a JSON file
    with open("data/physics_results.json", "w") as f:
        json.dump(results, f)

    print(f"Correct answers: {correct_count}/20")

if __name__ == "__main__":
    main()