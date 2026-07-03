#!/usr/bin/env python3
import sys
import json

def verify_egress_policy():
    registry_path = "has_live_project_tracker/data/provider_adapter_registry.json"
    policy_path = "has_live_project_tracker/data/provider_data_egress_policy.json"
    
    try:
        with open(registry_path, "r") as f:
            registry = json.load(f)
        with open(policy_path, "r") as f:
            policy = json.load(f)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

    classes = policy.get("content_classes", {})
    
    # Check that SECRET_OR_CREDENTIAL and CUSTOMER_DATA have no allowed destinations
    for cls_name in ["SECRET_OR_CREDENTIAL", "CUSTOMER_DATA", "FOUNDER_PRIVATE"]:
        destinations = classes.get(cls_name, {}).get("allowed_destinations", [])
        if destinations:
            print(f"❌ Verification failed: {cls_name} has allowed destinations: {destinations}")
            sys.exit(1)

    for provider in registry:
        if not provider.get("data_egress_policy_ref"):
            print(f"❌ Verification failed: Provider {provider.get('provider_id')} lacks data_egress_policy_ref.")
            sys.exit(1)

    print("🟢 Provider data egress policy verification PASSED.")
    return True

if __name__ == "__main__":
    verify_egress_policy()
