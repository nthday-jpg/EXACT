import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

from openai import OpenAI
client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

models_to_try = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro"
]

for model in models_to_try:
    print(f"Trying model: {model}...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        print(f"  Success! Response: {response.choices[0].message.content.strip()}")
        break
    except Exception as e:
        print(f"  Failed with error: {e}")
