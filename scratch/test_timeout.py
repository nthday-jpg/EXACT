import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("HF_API_KEY"),
    base_url="https://router.huggingface.co/v1"
)

models_to_test = [
    "Qwen/Qwen3-8B:featherless-ai",
    "Qwen/Qwen2.5-7B-Instruct"
]

for model in models_to_test:
    print(f"Testing model: {model}...")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            timeout=15.0
        )
        print(f"Success! Response: {resp.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"Failed: {e}")
