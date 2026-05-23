import json
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from src.llm.llm_client import LLMClient

import json

def run_pipeline(llm_output_string):
    try:
        # Direct parsing without regex struggles
        data = json.loads(llm_output_string)
        python_script = data["python_code"]
        
        # Execute the python script safely
        local_vars = {}
        exec(python_script, {}, local_vars)
        
        final_ans = local_vars.get("ans")
        final_unit = local_vars.get("unit")
        
        return final_ans, final_unit
    except json.JSONDecodeError:
        return None, "Failed to parse LLM response as valid JSON"
    except Exception as e:
        return None, f"Execution error: {str(e)}"

def main():
    load_dotenv()
    api_key = os.getenv("HF_API_KEY")
    model = "Qwen/Qwen3-8B:together"
    instructions = Path("src/llm/instructions/physics_solver.md").read_text("utf-8")
    df = pd.read_csv("data/processed/physics.csv")
    sampled_df = df.sample(n=10, random_state=42)

    llm_client = LLMClient(
        model_name=model,
        api_key=api_key,
        system_prompt=instructions,
        extra_body={
        "chat_template_kwargs": {"enable_thinking": False},
        }
    )
    rows = []

    for i, row in sampled_df.iterrows():
        print(f"Processing question {i+1}")
        question = row["question"]
        correct_answer = row["answer"]
        correct_units = row["unit"]

        print(f"Question: {question}")

        response = llm_client.generate(question, max_tokens=1024)
        ans, unit = run_pipeline(response)
        print(f"Model answer: {ans} {unit}")
        print(f"Correct answer: {correct_answer} {correct_units}")
        rows.append({
            "question": question,
            "correct_answer": correct_answer,
            "correct_units": correct_units,
            "model_answer": ans,
            "model_units": unit,
            "response": response
        })
    
    json.dump(rows, open("data/physics_results_python.json", "w"), indent=4)

if __name__ == "__main__":
    main()



    