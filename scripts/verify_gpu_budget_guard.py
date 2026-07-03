#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def verify_budget():
    print("Executing GPU Budget Guard Verification...")
    
    state_file = DATA_DIR / "gpu_pod_adapter_state.json"
    budget_file = DATA_DIR / "gpu_budget_policy.json"
    
    if not state_file.exists():
        print("🟢 No GPU Pod registered. Budget Guard skipped.")
        return True
        
    with open(state_file, "r") as f:
        state = json.load(f)
        
    is_online = state.get("status") == "ONLINE"
    
    if is_online:
        if not budget_file.exists():
            print("❌ Verification failed: GPU pod is ONLINE but gpu_budget_policy.json is missing.")
            sys.exit(1)
            
        with open(budget_file, "r") as f:
            budget = json.load(f)
            
        session_cost = budget.get("current_session_estimated_cost", 0.0)
        daily_limit = budget.get("daily_budget_usd", 0.0)
        weekly_limit = budget.get("weekly_budget_usd", 0.0)
        monthly_limit = budget.get("monthly_budget_usd", 0.0)
        
        # Validation checks
        if session_cost > daily_limit:
            print(f"❌ Verification failed: Current session cost ({session_cost}) exceeds daily budget limit ({daily_limit}).")
            sys.exit(1)
            
        if budget.get("budget_status") == "EXCEEDED":
            # If budget exceeded, make sure no Tier 3 tasks are allowed
            routing_file = DATA_DIR / "model_routing_policy.json"
            if routing_file.exists():
                with open(routing_file, "r") as rf:
                    routing = json.load(rf)
                # Find heavy routes
                for route in routing.get("routing", []):
                    if route.get("tier") == "heavy" and route.get("default_model_class") == "ollama_gpu_pod":
                        print("❌ Verification failed: Budget exceeded but Tier 3 task routing remains active.")
                        sys.exit(1)
                        
        # Product 002 R2+ safety validation
        if state.get("product_002_r2_authorized", False):
            print("❌ Verification failed: Product 002 R2+ authorization changed without founder approval.")
            sys.exit(1)
            
    print("🟢 GPU Budget Guard verification PASSED.")
    return True

if __name__ == "__main__":
    verify_budget()
