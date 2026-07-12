#!/usr/bin/env python3
"""H1D.7 — inventory outbound network/process primitives and classify them."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATTERNS = {
    "urllib": re.compile(r"\burllib\b"),
    "requests": re.compile(r"\brequests\.(get|post|put|delete|request|Session)\b"),
    "httpx": re.compile(r"\bhttpx\."),
    "aiohttp": re.compile(r"\baiohttp\b"),
    "socket": re.compile(r"\bsocket\.(socket|create_connection)\b"),
    "subprocess": re.compile(r"\bsubprocess\.(run|Popen|call|check_output|check_call)\b"),
    "Popen": re.compile(r"\bPopen\s*\("),
    "os.system": re.compile(r"\bos\.system\s*\("),
    "api.openai.com": re.compile(r"api\.openai\.com"),
    "api.anthropic.com": re.compile(r"api\.anthropic\.com"),
    "localhost:1234": re.compile(r"localhost:1234|127\.0\.0\.1:1234"),
    "ollama": re.compile(r"\bollama\b"),
    "grok_cli": re.compile(r"""['\"]grok['\"]"""),
    "gemini_cli": re.compile(r"""['\"]gemini['\"]"""),
}

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".tox", "coverage", ".mypy_cache",
}
EXTS = {".py", ".ts", ".tsx", ".js", ".sh"}


def classify(rel: str, pattern: str, snippet: str) -> dict:
    owner = rel.split("/")[0] if "/" in rel else rel
    call_type = pattern
    if rel.startswith("tests/") or "/test_" in rel:
        cat = "test_fixture"
    elif rel in ("scripts/council/gateway.py", "scripts/council/spend_gate.py"):
        cat = "approved_exception"
    elif pattern in ("api.openai.com", "api.anthropic.com") and "model_adapters" in rel:
        if "urlopen" in snippet or "Request(" in snippet:
            cat = "violation" if "GatewayRequest" not in snippet else "model_dispatch"
        else:
            cat = "model_dispatch"  # endpoint identity; remediated via gateway execute
    elif pattern in ("subprocess", "Popen") and any(
        x in snippet for x in ("grok", "gemini", "ollama", "claude")
    ):
        cat = "model_dispatch" if "gateway" not in rel and "spend_gate" not in rel else "approved_exception"
    elif pattern == "subprocess":
        cat = "local_process_invocation"
    elif pattern in ("urllib", "requests", "httpx", "aiohttp", "socket"):
        if "adapter" in rel or "model" in rel:
            cat = "model_dispatch"
        else:
            cat = "non_dispatch_network_use"
    elif pattern in ("ollama", "grok_cli", "gemini_cli", "localhost:1234"):
        cat = "model_dispatch"
    else:
        cat = "infrastructure_command"

    remediation = {
        "approved_exception": "none",
        "test_fixture": "none",
        "violation": "route_through_CouncilDispatchGateway_or_remove",
        "model_dispatch": "must_use_gateway_for_execute",
        "local_process_invocation": "review_if_model_related",
        "non_dispatch_network_use": "document_or_allowlist",
        "infrastructure_command": "document_or_allowlist",
    }.get(cat, "review")

    return {
        "file": rel,
        "pattern": pattern,
        "call_type": call_type,
        "owner": owner,
        "classification": cat,
        "remediation_status": remediation,
        "snippet": snippet[:160],
    }


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in EXTS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(p.relative_to(ROOT))
        for name, pat in PATTERNS.items():
            for i, line in enumerate(text.splitlines(), 1):
                if pat.search(line):
                    entry = classify(rel, name, line.strip())
                    entry["line"] = i
                    hits.append(entry)

    # Summary counts
    by_class: dict[str, int] = {}
    for h in hits:
        by_class[h["classification"]] = by_class.get(h["classification"], 0) + 1

    report = {
        "schema": "h1d7-outbound-inventory-v1",
        "total_hits": len(hits),
        "by_classification": by_class,
        "critical_model_paths": [
            h for h in hits
            if "model_adapters" in h["file"] or h["file"].startswith("scripts/council/")
        ],
        "entries": hits,
    }
    blob = json.dumps(report, indent=2)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(blob + "\n", encoding="utf-8")
        print(f"wrote {out_path} ({len(hits)} hits)")
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
