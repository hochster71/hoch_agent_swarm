#!/usr/bin/env python3
"""HELM local-model discovery — inventory the local brains (Ollama / LM Studio).

Queries the local runtime at HELM_LOCAL_MODEL_URL (Ollama /api/tags) and writes an
honest inventory to coordination/goal/local_models.json. If no endpoint is set or it is
unreachable, it reports that honestly (NOT_CONFIGURED / UNREACHABLE) — never invents models.

Usage:  export HELM_LOCAL_MODEL_URL=http://localhost:11434
        python3 scripts/helm_local_discover.py
"""
from __future__ import annotations
import json, os, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "coordination" / "goal" / "local_models.json"


def discover() -> dict:
    base = os.environ.get("HELM_LOCAL_MODEL_URL")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not base:
        return {"schema": "HELM_LOCAL_MODELS_v1", "checked_at": now,
                "status": "NOT_CONFIGURED", "reason": "HELM_LOCAL_MODEL_URL unset", "models": []}
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=8) as r:
            data = json.loads(r.read().decode())
        models = [{"name": m.get("name"), "size": m.get("size"),
                   "family": (m.get("details") or {}).get("family")}
                  for m in (data.get("models") or [])]
        return {"schema": "HELM_LOCAL_MODELS_v1", "checked_at": now, "endpoint": base,
                "status": "AVAILABLE" if models else "REACHABLE_NO_MODELS",
                "count": len(models), "models": models,
                "note": "local brains — preferred for private-data (family/home/finance) capabilities"}
    except Exception as e:
        return {"schema": "HELM_LOCAL_MODELS_v1", "checked_at": now, "endpoint": base,
                "status": "UNREACHABLE", "reason": f"{type(e).__name__}: {e}", "models": []}


def main() -> int:
    d = discover()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, indent=2) + "\n")
    print(f"Local models: {d['status']} — {d.get('count', 0)} found → {OUT}")
    for m in d.get("models", []):
        print(f"  · {m['name']} ({m.get('family') or '?'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
