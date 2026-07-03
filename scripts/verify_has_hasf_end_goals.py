#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("Executing HAS/HASF End Goals Verification...")
    files = [
        "docs/mission/HAS_HASF_END_GOALS_LOCK.md",
        "docs/mission/HAS_HASF_24_7_REMOTE_RUNTIME_REQUIREMENTS.md",
        "docs/mission/HELM_AUTONOMOUS_MODEL_RUNNER_DOCTRINE.md"
    ]
    
    for f in files:
        path = ROOT / f
        if not path.exists():
            print(f"❌ Verification failed: {f} does not exist.")
            sys.exit(1)
            
        content = path.read_text()
        if "founder" not in content.lower() and "release" not in content.lower():
            print(f"❌ Verification failed: {f} is missing safety gate clauses.")
            sys.exit(1)
            
        print(f"🟢 {f} exists and verified.")
        
    print("✅ HAS/HASF End Goals verification PASSED.")

if __name__ == "__main__":
    main()
