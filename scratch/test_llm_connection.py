import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
print("GEMINI_API_KEY is set:", api_key is not None)

try:
    from openai import OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    response = client.chat.completions.create(
        model="gemini-1.5-flash",
        messages=[{"role": "user", "content": "Hello, write a short word."}],
        max_tokens=10
    )
    print("API Response:", response.choices[0].message.content.strip())
except Exception as e:
    print("Error calling API:", e)
