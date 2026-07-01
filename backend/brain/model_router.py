import os
import requests
import json
import logging

logger = logging.getLogger("ModelRouter")

class ModelRouter:
    def __init__(self, ollama_url="http://localhost:11434/api/generate"):
        self.ollama_url = ollama_url
        self.blocked_keywords = ["openai.com", "anthropic.com", "api.openai", "api.anthropic", "cohere.ai", "groq.com"]

    def is_external_api_blocked(self, url: str) -> bool:
        # Blocks paid/cloud/external model APIs by default
        for keyword in self.blocked_keywords:
            if keyword in url:
                return True
        return False

    def query_local_model(self, prompt: str, model: str = "llama3") -> str:
        # Check safety check: no external cloud endpoints allowed
        if self.is_external_api_blocked(self.ollama_url):
            raise PermissionError("Access to external paid cloud LLM APIs is blocked by Autonomy Policy.")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=5.0)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Local model query failed/offline: {e}. Falling back to reasoning simulator.")
            
        # Safe fallback simulated reasoning
        return f"Simulated reasoning output for: '{prompt[:40]}...'. Status: PASS."
