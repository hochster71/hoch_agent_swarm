#!/usr/bin/env python3
import os
import json
import sys

def verify_private_first_doctrine():
    base_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."
    
    # 1. Verify doctrine files exist
    docs = [
        "docs/doctrine/HOCH_PRIVATE_FIRST_DOCTRINE.md",
        "docs/doctrine/HAS_HASF_PUBLIC_PRIVATE_BOUNDARY.md",
        "docs/doctrine/PROMPT_BRAIN_IP_PROTECTION.md",
        "docs/doctrine/APP_STORE_EXCEPTION_POLICY.md",
        "docs/doctrine/EXTERNAL_ENGAGEMENT_HOLD_POLICY.md"
    ]
    for d in docs:
        path = os.path.join(base_dir, d)
        if not os.path.exists(path):
            print(f"Error: Doctrine file {d} is missing.")
            sys.exit(1)
            
    # 2. Verify doctrine gate exists and check values
    gate_path = os.path.join(base_dir, "data/doctrine/private_first_doctrine_gate.json")
    if not os.path.exists(gate_path):
        print("Error: private_first_doctrine_gate.json is missing.")
        sys.exit(1)
        
    try:
        with open(gate_path, "r", encoding="utf-8") as f:
            gate = json.load(f)["private_first_doctrine_gate"]
    except Exception as e:
        print(f"Error parsing doctrine gate: {e}")
        sys.exit(1)
        
    # Asset assertions
    assert gate["private_brain_required"] is True, "Private Brain Required check failed."
    assert gate["external_company_engagement_allowed"] is False, "External Company Engagement must be blocked."
    assert gate["investor_engagement_allowed"] is False, "Investor Engagement must be blocked."
    assert gate["app_store_exception_allowed"] is True, "App Store Exception must be allowed."
    assert gate["prompt_registry_private"] is True, "Prompt Registry must be private."
    assert gate["evidence_ledgers_private"] is True, "Evidence Ledgers must be private."
    assert gate["swarm_architecture_private"] is True, "Swarm Architecture must be private."
    assert gate["hasf_factory_private"] is True, "HASF Factory must be private."
    assert gate["remote_relay_private_runtime_allowed"] is True, "Remote Relay Private Runtime must be allowed."
    assert gate["paid_pilot_external_send_allowed"] is False, "Paid Pilot External Send must be blocked."
    assert gate["paid_pilot_internal_package_allowed"] is True, "Paid Pilot Internal Package must be allowed."
    assert gate["app_outputs_public_allowed"] is True, "App Outputs Public must be allowed."
    assert gate["public_claims_require_evidence"] is True, "Public Claims Require Evidence check failed."
    assert gate["michael_approval_required_for_external_disclosure"] is True, "Michael Approval check failed."
    assert gate["final_verdict"] == "PRIVATE_FIRST_GO", "Final verdict must be PRIVATE_FIRST_GO."
    
    print("PRIVATE_FIRST_DOCTRINE: GO")
    return True

if __name__ == "__main__":
    verify_private_first_doctrine()
