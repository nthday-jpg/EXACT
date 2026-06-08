import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print("API Key set:", api_key is not None)

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
headers = {"Content-Type": "application/json"}
payload = {
    "contents": [{"parts": [{"text": "Hello, write a single word."}]}]
}

try:
    response = requests.post(url, headers=headers, json=payload)
    print("Status code:", response.status_code)
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print("Request failed:", e)
