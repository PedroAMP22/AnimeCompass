import requests
import json

class OllamaClient:
    def __init__(self, model="llama3.2", base_url="http://localhost:11434"):
        self.base_url = f"{base_url}/api/generate"
        self.model = model

    def prompt(self, system_prompt, user_input):
        payload = {
            "model": self.model,
            "prompt": f"System: {system_prompt}\nUser: {user_input}",
            "stream": False
        }
        response = requests.post(self.base_url, json=payload)
        return response.json().get("response", "")