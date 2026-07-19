#!/usr/bin/env python3
import os
import sys
import argparse

# Resolve workspace root and inject into python path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT)

from backend.audit_factory.service import HAFService

def main():
    parser = argparse.ArgumentParser(description="Run HAF Certification Assessment")
    parser.add_argument("--profile", default="helm_common", help="Profile to execute (e.g., helm_common, hasf_initial)")
    parser.add_argument("--scope", default="HELM_COMMON", help="Scope of the assessment")
    args = parser.parse_args()

    print(f"Starting HAF Assessment for profile '{args.profile}', scope '{args.scope}'...")
    os.environ["HAF_RUNNING"] = "1"

    try:
        service = HAFService(workspace_root=ROOT)
        summary = service.run_assessment(profile_name=args.profile, scope=args.scope)
        print("\nAssessment Run Complete!")
        print(f"  Run ID:    {summary['run_id']}")
        print(f"  Decision:  {summary['decision']}")
        print(f"  Controls:  {summary.get('controls_count', 0)}")
        print(f"    PASS:    {summary.get('pass_count', 0)}")
        print(f"    PASS_CANDIDATE: {summary.get('pass_candidate_count', 0)}")
        print(f"    HOLD:    {summary.get('hold_count', 0)}")
        print(f"    FAIL:    {summary.get('fail_count', 0)}")
        print(f"  Findings:  {summary['findings_count']} open finding(s)")
        print(f"  Evidence:  {summary['evidence_count']} artifact(s) indexed")
        
        reasons = summary.get('reasons', [])
        if reasons:
            print("\nReasons/Blockers:")
            for r in reasons:
                print(f"  • {r['control_id']}: {r['reason']}")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error executing assessment: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
