import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

def call_llm(prompt: str, model: str = "lgai/exaone-3-5-32b-instruct") -> str:
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data)

    try:
        resp_json = response.json()
    except Exception:
        raise RuntimeError(f"Failed to parse JSON from Together API: {response.text}")

    if "choices" not in resp_json:
        print(f"Together API error: {resp_json}")
        raise RuntimeError(f"Together API error: {resp_json}")

    return resp_json["choices"][0]["message"]["content"]
