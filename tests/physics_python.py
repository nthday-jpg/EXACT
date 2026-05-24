import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from dotenv import load_dotenv
from src.llm.llm_client import LLMClient
from time import time

import math 
import sympy

from src.physics.llm_execution import execute_llm_code
from src.physics.preprocessing import preprocess

def safe_execute_physics_code(llm_output_string):
    try:
        return execute_llm_code(llm_output_string)
        
    except json.JSONDecodeError:
        return None, "JSON_PARSE_ERROR"
    except Exception as e:
        return None, f"EXECUTION_ERROR: {str(e)}"


def process_question(index, question_raw, correct_answer, correct_units, model, api_key, instructions, heuristic):
    question_raw = preprocess(question_raw)
    question = heuristic + "\n\n" + question_raw
    start = time()
    llm_client = LLMClient(
        model_name=model,
        api_key=api_key,
        system_prompt=instructions,
        temperature=0.01,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        }
    )
    response = llm_client.generate(question)
    total_tokens = response["total_tokens"]
    input_tokens = response["input_tokens"]
    output_tokens = response["output_tokens"]
    content = response["content"]
    ans, unit = safe_execute_physics_code(content)
    end = time()

    return {
        "index": index,
        "time_taken_seconds": end - start,
        "total_tokens": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "question": question_raw,
        "correct_answer": correct_answer,
        "correct_units": correct_units,
        "model_answer": ans,
        "model_units": unit,
        "response": content,
    }

def main():
    load_dotenv()
    api_key = os.getenv("HF_API_KEY")
    model = "Qwen/Qwen3-8B:featherless-ai"
    operating = Path("src/physics/instructions/operating.md").read_text("utf-8")
    heuristic = Path("src/physics/instructions/heuristic.md").read_text("utf-8")
    instructions = operating
    df = pd.read_csv("data/processed/physics.csv")
    sampled_df = df.sample(n=20, random_state=11)
    rows = []
    time_start = time()
    try:
        tasks = [
            (i, row["question"], row["answer"], row["unit"], model, api_key, instructions, heuristic)
            for i, row in sampled_df.iterrows()
        ]
        max_workers = min(8, len(tasks)) or 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_question, *task) for task in tasks]
            for future in as_completed(futures):
                result = future.result()
                print(f"Processed question {result['index'] + 1}")
                print(f"Question: {result['question']}")
                print(f"Time taken: {result['time_taken_seconds']:.2f} seconds")
                print(
                    f"Tokens - Total: {result['total_tokens']}, Input: {result['input_tokens']}, "
                    f"Output: {result['output_tokens']}"
                )
                print(f"Model Answer: {result['model_answer']} {result['model_units']}")
                print(f"Correct Answer: {result['correct_answer']} {result['correct_units']}")
                print("-" * 50)
                rows.append(result)
    finally:
        json.dump(rows, open("data/physics_results_python.json", "w"), indent=4)
        time_end = time()
        print(f"Total time taken for processing: {time_end - time_start:.2f} seconds")
if __name__ == "__main__":
    main()



    