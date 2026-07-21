#!/usr/bin/env python3
"""authority_gate.py — resume-trigger detection for authority-gated protocol runs.

PROTO-EXP-002 (2026-07-21). The seven-stage protocol modelled a LINEAR run because every
prior application was agent-completable end to end. A founder-gated control splits the run
across sessions separated by an action the agent can neither perform nor witness.

The finding was NOT a missing stage. It was a missing TRANSITION:

    Stage 3 ──┬── repair complete ─────────────► Stage 4
              │
              └── awaits authority
                        │
                  BLOCKED_AWAITING_AUTHORITY
                        │
                  authority OBSERVED ──────────► Stage 4

    Stages say what work exists. Transitions say when work becomes ELIGIBLE.

DESIGN RULE (founder, 2026-07-21): the protocol must not ASSUME the authority action
happened — it must DETECT that it happened. A resume triggered by assumption would make
the authority boundary the one unverified link in an otherwise evidence-driven chain.

So this module never asks "has enough time passed" or "did the founder say so". It asks
the authoritative source and reports what it saw. Absence of evidence resumes nothing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict

REPO = "hochster71/hoch_agent_swarm"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh(path: str) -> tuple[bool, Any]:
    """Query GitHub. Returns (reachable, payload). A failure to REACH the API is NOT
    evidence of absence — it is UNOBSERVED, and must not be reported as OBSERVED_ABSENT."""
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    except Exception as e:
        return False, str(e)[:200]
    if r.returncode == 0:
        try:
            return True, json.loads(r.stdout)
        except Exception:
            return True, r.stdout[:200]
    body = (r.stdout or r.stderr or "").lower()
    if "not protected" in body or '"status":"404"' in body or "404" in body:
        return True, None            # reached the API; it authoritatively says absent
    return False, (r.stderr or r.stdout)[:200]   # could not reach / not authorised


def observe_branch_protection(branch: str = "master") -> Dict[str, Any]:
    ok, payload = _gh(f"repos/{REPO}/branches/{branch}/protection")
    if not ok:
        return {"control": "RC23-BRANCH-PROTECTION", "state": "UNOBSERVED",
                "reason": str(payload)[:200], "observed_at": _now()}
    if payload is None:
        return {"control": "RC23-BRANCH-PROTECTION", "state": "OBSERVED_ABSENT",
                "detail": "GitHub reports branch not protected", "observed_at": _now()}
    return {"control": "RC23-BRANCH-PROTECTION", "state": "OBSERVED_PRESENT",
            "enforce_admins": (payload.get("enforce_admins") or {}).get("enabled"),
            "required_signatures": (payload.get("required_signatures") or {}).get("enabled"),
            "observed_at": _now()}


def observe_commit_signing(n: int = 20) -> Dict[str, Any]:
    """git's %G? — G good, B bad, U untrusted, N none. Reads the local object store, which
    holds the same commit objects the remote does, so the signature bytes are authoritative."""
    try:
        out = subprocess.run(["git", "log", f"-{n}", "--format=%G?"],
                             capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {"control": "COMMIT-SIGNING", "state": "UNOBSERVED", "reason": str(e)[:200]}
    if out.returncode != 0:
        return {"control": "COMMIT-SIGNING", "state": "UNOBSERVED",
                "reason": (out.stderr or "")[:200]}
    marks = [m for m in out.stdout.split() if m]
    signed = sum(1 for m in marks if m in ("G", "U"))
    return {"control": "COMMIT-SIGNING",
            "state": "OBSERVED_PRESENT" if signed else "OBSERVED_ABSENT",
            "verifiable_signatures": signed, "commits_examined": len(marks),
            "observed_at": _now()}


def resume_eligible() -> Dict[str, Any]:
    """THE TRANSITION. Stage 4 becomes eligible only on OBSERVED_PRESENT evidence.

    Three-valued deliberately. UNOBSERVED (API unreachable, gh unauthenticated) must not
    collapse into OBSERVED_ABSENT — "we could not look" is not "it is not there", and a
    resume gate that conflates them would either stall forever or advance on ignorance.
    """
    bp = observe_branch_protection()
    cs = observe_commit_signing()
    states = {bp["control"]: bp["state"], cs["control"]: cs["state"]}
    if any(v == "UNOBSERVED" for v in states.values()):
        verdict, why = "UNKNOWN", "at least one control could not be observed"
    elif all(v == "OBSERVED_PRESENT" for v in states.values()):
        verdict, why = "RESUME_ELIGIBLE", "authority action detected on all gated controls"
    else:
        verdict, why = "BLOCKED_AWAITING_AUTHORITY", "authority action not yet detected"
    return {"experiment": "PROTO-EXP-002", "checked_at": _now(),
            "protocol_stage": 3, "next_stage": 4,
            "verdict": verdict, "reason": why,
            "detected_not_assumed": True, "observations": [bp, cs],
            "note": ("stages unchanged; this supplies the missing TRANSITION between "
                     "stage 3 and stage 4, not an eighth stage")}


if __name__ == "__main__":
    r = resume_eligible()
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["verdict"] == "RESUME_ELIGIBLE" else 1)
