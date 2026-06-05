import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("HF_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

try:
    response = requests.get("https://router.huggingface.co/v1/models", headers=headers)
    response.raise_for_status()
    models = response.json()
    
    target = None
    for m in models.get("data", []):
        if m["id"] == "Qwen/Qwen3-235B-A22B-Instruct-2507":
            target = m
            break
            
    if target:
        print("Model Details:")
        import json
        print(json.dumps(target, indent=2))
    else:
        print("Model not found in list.")
except Exception as e:
    print(f"Error fetching details: {e}")
