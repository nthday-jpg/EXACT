import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient
from src.llm.prompts import (
    COMBINED_GLOSSARY_AND_TRANSLATION_SYSTEM_PROMPT,
    COMBINED_GLOSSARY_AND_TRANSLATION_USER_PROMPT_TEMPLATE
)

load_dotenv()

nl_list = [
    "There exists someone who has obtained both MOS certifications in Word and Excel.",
    "If x did not register for the seminar, then x is not allowed to submit the report.",
    "If x registered for the seminar, then x has completed all requirements to register for the seminar.",
    "If x did not submit the required report, then x is not allowed to submit the report for the seminar.",
    "If x is eligible to attend the seminar, then x has the required certifications.",
    "Registering for the seminar does not imply completing all requirements to register, according to the premises"
]

nl_content = ""
for i, nl in enumerate(nl_list, start=1):
    nl_content += f"{i}. {nl}\n"

user_prompt = COMBINED_GLOSSARY_AND_TRANSLATION_USER_PROMPT_TEMPLATE.format(nl_content=nl_content.strip())

print("Initializing client...")
client = LLMClient(
    model_name="Qwen/Qwen3-8B:featherless-ai",
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_API_KEY"),
    temperature=0.1
)
client.tokenizer = None  # Force chat completions to avoid completions choices message bug

# We will modify LLMClient.generate call locally to pass timeout, or use a custom raw completions call
print("Sending request to Qwen/Qwen3-8B:featherless-ai...")
try:
    # We can invoke generate directly
    res = client.generate(
        prompt=user_prompt,
        system_prompt=COMBINED_GLOSSARY_AND_TRANSLATION_SYSTEM_PROMPT,
        max_tokens=2048
    )
    print("Response succeeded!")
    print("Length of response:", len(res["content"]))
    print("Content:")
    print(res["content"])
except Exception as e:
    print(f"Failed with exception: {e}")
