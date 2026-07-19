import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROK_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
models = response.json()

for model in models.get("data", []):
    print(model["id"])
