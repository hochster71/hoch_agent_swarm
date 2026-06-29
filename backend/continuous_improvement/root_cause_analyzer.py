import json
from pathlib import Path
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

class RootCauseAnalyzer:
    def __init__(self):
        pass
        
    def analyze_failure(self, error_message: str, stack_trace: str) -> dict:
        # Determine likely component based on keywords
        suspect_component = "unknown"
        if "playwright" in error_message.lower() or "page.goto" in error_message.lower():
            suspect_component = "frontend_e2e"
        elif "sqlite" in error_message.lower() or "database is locked" in error_message.lower():
            suspect_component = "database"
        elif "ollama" in error_message.lower() or "connection refused" in error_message.lower():
            suspect_component = "model_provider"
        elif "sign" in error_message.lower() or "signing" in error_message.lower():
            suspect_component = "signing_policy"
            
        analysis = {
            "timestamp": now_iso(),
            "error_summary": error_message[:200],
            "suspect_component": suspect_component,
            "root_cause_guess": f"Failure in {suspect_component} matching pattern: {error_message[:50]}",
            "recommended_action": f"Verify connection/state of {suspect_component}"
        }
        return analysis
