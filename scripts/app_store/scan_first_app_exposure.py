#!/usr/bin/env python3
import os
import json

def run_exposure_scan():
    base_dir = os.path.dirname(os.path.abspath(__file__)) + "/../.."
    app_dir = os.path.join(base_dir, "apps/rmf_evidence_review_companion")
    
    forbidden_terms = [
        "Prompt Brain", "HASF", "agent swarm", "prompt registry",
        "evidence ledger", "paid pilot", "relays"
    ]
    
    leaked = []
    if os.path.exists(app_dir):
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                if file.endswith((".dart", ".yaml", ".json")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for term in forbidden_terms:
                                if term in content:
                                    leaked.append({"file": file, "term": term})
                    except Exception:
                        pass
                        
    scan_result = {
        "forbidden_terms_found": len(leaked) > 0,
        "leak_details": leaked,
        "verdict": "SAFE_TO_BUILD" if len(leaked) == 0 else "NEEDS_REMEDIATION"
    }
    
    output_path = os.path.join(base_dir, "data/app_store/first_app_rc1_exposure_scan.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"exposure_scan": scan_result}, f, indent=2)
        
    print(f"Exposure scan complete. Verdict: {scan_result['verdict']}")
    return scan_result

if __name__ == "__main__":
    run_exposure_scan()
