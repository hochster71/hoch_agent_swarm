#!/usr/bin/env python3
"""DEPRECATED shim (2026-07-22): superseded minutes after authoring by the
table-driven scripts/goal/refresh_enforcement_proofs.py, which handles
REQ-GOV-002, REQ-GOV-003 and REQ-ES-002 with the identical commit-bound,
fail-closed proof convention. Kept as a shim so any reference to this path
keeps working; delegates to the general refresher for REQ-GOV-002 only.
"""
import runpy
import sys
from pathlib import Path

sys.argv = [sys.argv[0], "REQ-GOV-002"]
runpy.run_path(str(Path(__file__).with_name("refresh_enforcement_proofs.py")),
               run_name="__main__")
