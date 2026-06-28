#!/usr/bin/env python3
import sys
import json
import os

def check_policy(prompt_content=None):
    print("[gatekeeper] Loading policy and blocked actions...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    policy_path = os.path.join(base_dir, "control/authority_policy.json")
    blocked_path = os.path.join(base_dir, "control/blocked_actions.json")
    
    if not os.path.exists(policy_path) or not os.path.exists(blocked_path):
        print("[gatekeeper] FAIL: Policy files missing!")
        sys.exit(1)
        
    try:
        with open(policy_path, "r") as f:
            policy = json.load(f)
        with open(blocked_path, "r") as f:
            blocked_data = json.load(f)
    except Exception as e:
        print(f"[gatekeeper] FAIL: Failed to parse JSON config: {e}")
        sys.exit(1)

    # Cross-check policy blocked actions
    human_required = policy.get("human_approval_required", [])
    blocked_actions = [x["action"] for x in blocked_data.get("blocked_actions", [])]
    
    # Check that every blocked action requires human approval
    for act in blocked_actions:
        # Match either exact name or simplified string
        found = False
        for hr in human_required:
            if act in hr or hr in act:
                found = True
                break
        if not found:
            print(f"[gatekeeper] FAIL: Blocked action '{act}' not listed in human_approval_required policy!")
            sys.exit(1)
            
    # Verify that each blocked action in blocked_actions.json has performed=false
    for entry in blocked_data.get("blocked_actions", []):
        if entry.get("performed") is not False:
            print(f"[gatekeeper] FAIL: Blocked action '{entry['action']}' has performed=true!")
            sys.exit(1)

    # Optional content scanning to fail closed if a prompt requests active mutations
    if prompt_content:
        # Search for forbidden indicators in the prompt (e.g. "perform production deployment", "execute git push", etc.)
        content_lower = prompt_content.lower()
        forbidden_keywords = ["git push", "git merge", "production deployment", "deploy to production", "add secrets", "claim actual ato"]
        # Allow keywords only if accompanied by "blocked" or "no" or "must stop"
        for kw in forbidden_keywords:
            if kw in content_lower:
                # Basic context check: must contain negative assertions like "no git push" or "blocked"
                if "no " + kw not in content_lower and "blocked" not in content_lower and "must stop" not in content_lower and "not certified" not in content_lower:
                    print(f"[gatekeeper] FAIL: Prompt content requests unauthorized action '{kw}' without blocked-action gating context!")
                    sys.exit(1)
                    
    print("[gatekeeper] PASS: Closed-loop policy checks passed.")
    return True

if __name__ == "__main__":
    check_policy()
