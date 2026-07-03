#!/usr/bin/env python3
import sys
import json

def verify_budget():
    registry_path = "has_live_project_tracker/data/provider_adapter_registry.json"
    policy_path = "has_live_project_tracker/data/api_budget_policy.json"
    
    try:
        with open(registry_path, "r") as f:
            registry = json.load(f)
        with open(policy_path, "r") as f:
            policy = json.load(f)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

    budgets = policy.get("providers", {})
    for provider in registry:
        p_id = provider.get("provider_id")
        if provider.get("endpoint_type") == "api" and provider.get("enabled"):
            if p_id not in budgets:
                print(f"❌ Verification failed: Enabled API provider {p_id} lacks budget configuration.")
                sys.exit(1)
                
            p_budget = budgets[p_id]
            if p_budget.get("current_estimated_daily_cost", 0) > p_budget.get("daily_budget_usd", 0):
                print(f"❌ Verification failed: Provider {p_id} daily budget exceeded.")
                sys.exit(1)

    # Read and verify max_concurrent_missions from orchestration_bridge_control.json
    control_path = "has_live_project_tracker/data/orchestration_bridge_control.json"
    try:
        with open(control_path, "r") as f:
            control = json.load(f)
        if control.get("max_concurrent_missions", 1) > 1:
            print("❌ Verification failed: max_concurrent_missions > 1 during first-week bridge baseline.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

    print("🟢 API Budget Guard verification PASSED.")
    return True

if __name__ == "__main__":
    verify_budget()
