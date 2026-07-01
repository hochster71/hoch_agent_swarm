import os
import json

class PromptHistoryStore:
    def __init__(self):
        if os.path.exists("/app"):
            self.history_path = "/app/frontend/data/prompt_history.json"
        else:
            self.history_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/data/prompt_history.json"))
            
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

    def load_history(self) -> list:
        if not os.path.exists(self.history_path):
            return []
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_contract(self, contract: dict):
        history = self.load_history()
        history.append(contract)
        # Keep only the last 30 entries
        history = history[-30:]
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass
            
    def get_latest_contract(self) -> dict:
        history = self.load_history()
        if history:
            return history[-1]
        return {}
