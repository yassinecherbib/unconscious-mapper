import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("Listing models:")
try:
    for m in client.models.list():
        if "gemma" in m.name.lower():
            print(f"Gemma model: {m.name}")
        elif "gemini" in m.name.lower():
            print(f"Gemini model: {m.name}")
except Exception as e:
    print(f"Error: {e}")
