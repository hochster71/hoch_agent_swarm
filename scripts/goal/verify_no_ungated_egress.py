#!/usr/bin/env python3
"""REQ-ES-003 — no provider POST outside the spend gate.

Found by the council itself on its first live dispatch (Grok):
scripts/prompt_brain/model_adapters.py OpenAIAdapter.execute POSTs directly to
api.openai.com via urllib, bypassing SubprocessSpendGate entirely.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "ungated_egress_report.json"
GATED = {"scripts/council/spend_gate.py", "scripts/council/adapters.py"}
PROVIDERS = ("api.openai.com", "api.anthropic.com", "api.x.ai", "generativelanguage.googleapis.com")
offenders = []
for p in ROOT.rglob("*.py"):
    rel = str(p.relative_to(ROOT))
    if any(s in rel for s in ("node_modules", ".venv", "__pycache__", "docs/evidence", "archive/", "tests/")):
        continue
    if rel in GATED:
        continue
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if not any(h in src for h in PROVIDERS):
        continue
    if re.search(r"urlopen|requests\.post|httpx|aiohttp", src):
        hosts = sorted({h for h in PROVIDERS if h in src})
        offenders.append({"file": rel, "provider_hosts": hosts,
                          "defect": "PROVIDER_CALL_OUTSIDE_SPEND_GATE"})
report = {"requirement": "REQ-ES-003", "ungated_egress": offenders,
          "status": "PASS" if not offenders else "FAIL"}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(f"ungated provider-call sites: {len(offenders)}")
sys.exit(0 if not offenders else 1)
