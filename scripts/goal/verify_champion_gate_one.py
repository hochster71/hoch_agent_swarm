#!/usr/bin/env python3
"""One champion gate -> one exit code. Recomputes the gates, then reports THIS gate."""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
name = sys.argv[1] if len(sys.argv) > 1 else ""
subprocess.run([sys.executable, str(ROOT/"scripts/goal/verify_champion_gates.py")],
               cwd=str(ROOT), capture_output=True)
rep = json.loads((ROOT/"coordination/goal/champion_gates.json").read_text())
g = next((x for x in rep["gates"] if x["gate"] == name), None)
if not g:
    print(f"{name}: NO SUCH GATE"); sys.exit(1)
print(f"{name}: {g['status']} — {g['detail'][:70]}")
sys.exit(0 if g["status"] == "PASS" else 1)
