import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    # Try gemini-1.5-flash
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Hello, write a single word.")
    print("Official API Response:", response.text.strip())
except Exception as e:
    print("Official API Error:", e)
