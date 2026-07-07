import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import datetime, timezone
from pathlib import Path
from backend.runtime_governor import RuntimeGovernor


def main():
    parser = argparse.ArgumentParser(description="Advisory Runtime Governor Single Cycle Execution")
    parser.add_argument("--advisory", action="store_true", help="Run in advisory mode only")
    parser.add_argument("--evidence-dir", type=str, help="Directory to write decision record evidence")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000", help="Base URL of the FastAPI backend")
    
    args = parser.parse_args()
    
    if not args.advisory:
        print("ERROR: Runtime Governor must be run in --advisory mode.", file=sys.stderr)
        sys.exit(1)
        
    evidence_dir = args.evidence_dir
    if not evidence_dir:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        evidence_dir = f"docs/evidence/runtime/runtime_governor_advisory_{timestamp}"
        
    print(f"Initializing Runtime Governor in advisory mode...")
    gov = RuntimeGovernor(base_url=args.base_url)
    
    try:
        res = gov.evaluate(evidence_dir=evidence_dir)
        verdict = res["verdict"]
        print(f"Verdict: {verdict}")
        if res["reasons"]:
            print("Reasons:")
            for r in res["reasons"]:
                print(f"  - {r}")
        print(f"Evidence written to: {res['evidence_path']}")
        sys.exit(0)
    except Exception as e:
        print(f"FATAL: Governor run failed: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
