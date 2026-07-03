#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def verify_authorization():
    print("Executing Product 002 R2 Authorization Verification Gate...")
    
    state_file = DATA_DIR / "product_002_authorization_state.json"
    manifest_file = DATA_DIR / "product_002_r2_task_manifest.json"
    
    if not state_file.exists():
        print("❌ Verification failed: product_002_authorization_state.json is missing.")
        sys.exit(1)
        
    if not manifest_file.exists():
        print("❌ Verification failed: product_002_r2_task_manifest.json is missing.")
        sys.exit(1)
        
    with open(state_file, "r") as f:
        state = json.load(f)
    with open(manifest_file, "r") as f:
        manifest = json.load(f)
        
    # Check unauthorized R2 state safety rules
    is_r2_authorized = state.get("r2_authorized", False)
    authorized_by = state.get("authorized_by")
    
    if is_r2_authorized and not authorized_by:
        print("❌ Verification failed: R2 is marked authorized without founder signature details.")
        sys.exit(1)
        
    # Blocked scopes
    if state.get("production_release_authorized", False):
        print("❌ Verification failed: Production release authorization must remain false in R2.")
        sys.exit(1)
        
    if state.get("monetization_authorized", False):
        print("❌ Verification failed: Monetization authorization must remain false in R2.")
        sys.exit(1)
        
    if state.get("public_claims_authorized", False):
        print("❌ Verification failed: Public claims authorization must remain false in R2.")
        sys.exit(1)
        
    if state.get("customer_data_authorized", False):
        print("❌ Verification failed: Customer data handling authorization must remain false in R2.")
        sys.exit(1)
        
    # Verify R2 task manifest entries
    for task in manifest:
        task_id = task.get("task_id")
        
        if not task.get("risk_tier"):
            print(f"❌ Verification failed: Task {task_id} lacks risk_tier configuration.")
            sys.exit(1)
            
        if not task.get("required_model_tier"):
            print(f"❌ Verification failed: Task {task_id} lacks required_model_tier configuration.")
            sys.exit(1)
            
        # If Tier 3 task, ensure native 1.5B is blocked
        if task.get("required_model_tier") == "heavy":
            if "ollama_native" in task.get("allowed_adapters", []):
                # Ensure it's blocked
                print(f"❌ Verification failed: Task {task_id} allows ollama_native for Tier 3 execution.")
                sys.exit(1)
                
        # Check blocked adapters and forbidden actions mapping
        if "ollama_native" not in task.get("blocked_adapters", []):
            print(f"❌ Verification failed: Task {task_id} does not block ollama_native.")
            sys.exit(1)
            
    print("🟢 Product 002 R2 Authorization verification PASSED.")
    return True

if __name__ == "__main__":
    verify_authorization()
