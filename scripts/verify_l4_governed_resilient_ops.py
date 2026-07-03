#!/usr/bin/env python3
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def run_gate(script_path):
    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    return res.returncode == 0, res.stdout + res.stderr

def main():
    print("Executing L4 Governed Resilient Operations verification battery...")
    
    # 1. Verify required L3 gates
    gates = [
        "verify_has_hasf_end_goals.py",
        "verify_helm_autonomy_layer.py",
        "verify_24_7_remote_runtime.py",
        "verify_model_adapter_health.py",
        "verify_runtime_truth_freshness.py",
        "verify_no_secret_leakage.py",
        "verify_agent_output_quality.py",
        "verify_evidence_integrity.py",
        "verify_evidence_manifest_signature.py"
    ]
    
    for gate in gates:
        ok, log = run_gate(ROOT / f"scripts/{gate}")
        if not ok:
            print(f"❌ Verification failed: Gate '{gate}' returned error.")
            print(log)
            sys.exit(1)
        print(f"🟢 Gate '{gate}' passed.")

    # 2. Verify Chaos 6-10 evidence files exist
    chaos_files = [
        "chaos-06-stale-runtime-json.md",
        "chaos-07-evidence-write-failure.md",
        "chaos-08-forbidden-adapter-action.md",
        "chaos-09-prompt-injection-attempt.md",
        "chaos-10-github-vercel-adapter-failure.md"
    ]
    evidence_dir = ROOT / "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset"
    for f in chaos_files:
        if not (evidence_dir / f).exists():
            print(f"❌ Verification failed: Chaos evidence file '{f}' is missing.")
            sys.exit(1)
        print(f"🟢 Chaos evidence file '{f}' is verified.")

    # 3. Verify Product 002 R2+ is blocked and release/monetization are false
    state_file = DATA_DIR / "l4_governed_resilient_ops_state.json"
    if not state_file.exists():
        print("❌ Verification failed: l4_governed_resilient_ops_state.json is missing.")
        sys.exit(1)
        
    with open(state_file, "r") as f:
        state = json.load(f)
        
    if not state.get("product_002_r2_blocked", True):
        print("❌ Verification failed: Product 002 R2+ is unblocked without founder approval.")
        sys.exit(1)
        
    if state.get("live_release_authorized", False):
        print("❌ Verification failed: live_release_authorized is true.")
        sys.exit(1)
        
    if state.get("live_monetization_authorized", False):
        print("❌ Verification failed: live_monetization_authorized is true.")
        sys.exit(1)
        
    print("🟢 Product 002 and monetization guardrails are active.")
    print("✅ L4 Governed Resilient Operations verification PASSED.")

if __name__ == "__main__":
    main()
