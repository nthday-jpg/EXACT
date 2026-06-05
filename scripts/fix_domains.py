import json
import asyncio
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm.asyncio import tqdm_asyncio  # <--- Import async tqdm helper

from src.physics.router import classify_question 

load_dotenv()

hf_api_key = os.getenv("HF_API_KEY") 
CONCURRENCY_LIMIT = 10

def deduplicate_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_questions = {}
    for record in records:
        q = record.get("question")
        if q:
            seen_questions[q] = record
    return list(seen_questions.values())


async def process_single_record(record: Dict[str, Any], semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    question = record["question"]
    async with semaphore:
        try:
            classification = await asyncio.to_thread(
                classify_question,
                question=question,
                model_name="meta-llama/Llama-3.1-8B-Instruct:featherless-ai",
                api_key=hf_api_key,
                temperature=0.0
            )
            record["domains"] = classification.domains
            record["warnings"] = classification.warnings
                
        except Exception as e:
            # Note: Using tqdm.write prevents standard print statements 
            # from breaking/shredding the visual progress bar rendering
            tqdm_asyncio.write(f"Error processing question: {question[:30]}... Error: {e}")
            pass
            
    return record


async def main(input_file_path: str, output_file_path: str):
    print(f"Loading dataset from {input_file_path}...")
    with open(input_file_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    
    initial_count = len(records)
    print(f"Loaded {initial_count} records.")

    deduped_records = deduplicate_records(records)
    deduped_count = len(deduped_records)
    print(f"Deduplication complete. Kept {deduped_count} records (dropped {initial_count - deduped_count} duplicates).")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    print("Rerunning router for new domain mapping schema...")
    tasks = [process_single_record(record, semaphore) for record in deduped_records]
    
    # tqdm_asyncio.gather automatically handles monitoring the execution state 
    # of the scheduled tasks and draws a responsive progress bar
    updated_records = await tqdm_asyncio.gather(*tasks, desc="Routing Progress")

    print(f"Saving updated file to {output_file_path}...")
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(updated_records, f, indent=2, ensure_ascii=False)
        
    print("Process complete!")


if __name__ == "__main__":
    INPUT_FILE = "runs/physics_distillation_correct.json"
    OUTPUT_FILE = "runs/physics_distillation_re_routed.json"
    
    asyncio.run(main(INPUT_FILE, OUTPUT_FILE))