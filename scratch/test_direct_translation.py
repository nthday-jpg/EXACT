import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient
from src.logic.pipeline import LogicalReasoningPipeline

load_dotenv()

premises_nl = [
    "There exists someone who has obtained both MOS certifications in Word and Excel.",
    "If x did not register for the seminar, then x is not allowed to submit the report.",
    "If x registered for the seminar, then x has completed all requirements to register for the seminar.",
    "If x did not submit the required report, then x is not allowed to submit the report for the seminar.",
    "If x is eligible to attend the seminar, then x has the required certifications."
]
question = "Is it true that registering for the seminar does not imply completing all requirements to register, according to the premises?"

print("Initializing client...")
client = LLMClient(
    model_name="Qwen/Qwen3-8B:featherless-ai",
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_API_KEY"),
    temperature=0.1
)
client.tokenizer = None  # Force chat completions

pipeline = LogicalReasoningPipeline(use_local=False, llm_client=client)

# Patch to force is_finetuned to True for translation & pipeline checks
old_translate_list = pipeline.translation_pipeline.translate_list
def patched_translate_list(nl_list, max_new_tokens=None):
    orig_name = pipeline.llm_client.model_name
    pipeline.llm_client.model_name = "exact-qwen-lora"
    old_generate = pipeline.llm_client.generate
    def patched_generate(prompt, max_tokens=None, system_prompt=None):
        pipeline.llm_client.model_name = orig_name # Restore real name for API call
        try:
            return old_generate(prompt, max_tokens, system_prompt)
        finally:
            pipeline.llm_client.model_name = "exact-qwen-lora"
    pipeline.llm_client.generate = patched_generate
    try:
        return old_translate_list(nl_list, max_new_tokens)
    finally:
        pipeline.llm_client.model_name = orig_name
        pipeline.llm_client.generate = old_generate

pipeline.translation_pipeline.translate_list = patched_translate_list

# Also patch pipeline's own checks for is_finetuned (premise filtering, etc.)
old_run_pipeline = pipeline.run_pipeline
def patched_run_pipeline(premises_nl, conclusion_nl, question_type=None):
    orig_name = pipeline.llm_client.model_name
    pipeline.llm_client.model_name = "exact-qwen-lora"
    old_generate = pipeline.llm_client.generate
    def patched_generate(prompt, max_tokens=None, system_prompt=None):
        pipeline.llm_client.model_name = orig_name # Restore real name for API call
        try:
            return old_generate(prompt, max_tokens, system_prompt)
        finally:
            pipeline.llm_client.model_name = "exact-qwen-lora"
    pipeline.llm_client.generate = patched_generate
    try:
        return old_run_pipeline(premises_nl, conclusion_nl, question_type)
    finally:
        pipeline.llm_client.model_name = orig_name
        pipeline.llm_client.generate = old_generate

pipeline.run_pipeline = patched_run_pipeline

print("Running pipeline on sample 1...")
import time
start = time.time()
try:
    res = pipeline.run_pipeline(premises_nl, question)
    print("Success! Elapsed time:", time.time() - start)
    print("Answer:", res["answer"])
    print("Premises FOL:", res["premises_fol"])
    print("Conclusion FOL:", res["conclusion_fol"])
    print("Verification:", res["verification"]["result"])
    print("Reasoning:", res["reasoning"])
except Exception as e:
    print("Failed:", e)
