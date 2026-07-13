"""founder_gate.py — the iPhone founder gate. The only surface Michael must touch.

DESIGN CONSTRAINT (from the founder authority matrix, non-negotiable)
--------------------------------------------------------------------
Tapping APPROVE on a phone is the founder pressing the button. That is legitimate for
PROPOSE_ONLY items (deploy, publish, paid dispatch, price change) — HELM prepared and
proved them, Michael authorizes them.

It is NOT legitimate for FOUNDER_ONLY items. Rotating a key, accepting a legal agreement,
or moving money cannot be delegated to a tap that HELM then performs on his behalf — that
would convert "the final approval is real" into a rubber stamp, and hand the model exactly
the authority the matrix forbids it. So:

    PROPOSE_ONLY  -> APPROVE / DENY        (HELM executes on approval)
    FOUNDER_ONLY  -> ACKNOWLEDGE only      (Michael must do the act himself, elsewhere)

Every decision is appended to a hash-chained ledger so an approval cannot be forged or
silently rewritten later.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "coordination" / "founder" / "escalation_queue.jsonl"
DECISIONS = ROOT / "coordination" / "founder" / "decision_ledger.jsonl"

# Shared secret for the gate. Tailnet already restricts reachability; this is defence in
# depth so a device on the tailnet cannot approve without the token.
TOKEN_ENV = "HELM_FOUNDER_TOKEN"


def _token() -> str:
    return os.environ.get(TOKEN_ENV, "")


def authorized(presented: str | None) -> bool:
    tok = _token()
    if not tok:
        return False  # fail closed: no token configured => no approvals possible
    return bool(presented) and hmac.compare_digest(presented, tok)


def _read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _decided_ids() -> set[str]:
    return {d["decision_id"] for d in _read_jsonl(DECISIONS) if d.get("decision_id")}


def pending() -> list[dict[str, Any]]:
    """Escalations awaiting the founder, newest first, already-decided ones removed."""
    done = _decided_ids()
    items = [e for e in _read_jsonl(QUEUE) if e.get("decision_id") not in done]
    return sorted(items, key=lambda e: e.get("queued_at", 0), reverse=True)


def _last_hash() -> str:
    rows = _read_jsonl(DECISIONS)
    return rows[-1]["entry_hash"] if rows else "GENESIS"


# Which verbs are legal for which authority class.
LEGAL_VERBS = {
    "PROPOSE_ONLY": {"APPROVE", "DENY"},
    "FOUNDER_ONLY": {"ACKNOWLEDGE"},   # HELM must never execute these on a tap
    "AUTONOMOUS": {"ACKNOWLEDGE"},
}


def record_decision(decision_id: str, verb: str, *, authority: str,
                    note: str = "") -> tuple[bool, str]:
    """Append a hash-chained founder decision. Returns (ok, message)."""
    verb = verb.upper()
    allowed = LEGAL_VERBS.get(authority.upper(), {"ACKNOWLEDGE"})
    if verb not in allowed:
        return False, (
            f"REFUSED: '{verb}' is not permitted for {authority}. "
            f"{'A FOUNDER_ONLY act cannot be delegated to a tap — you must perform it yourself.' if authority.upper() == 'FOUNDER_ONLY' else ''}"
            f" Allowed: {sorted(allowed)}"
        )

    prev = _last_hash()
    row = {
        "decision_id": decision_id,
        "verb": verb,
        "authority": authority.upper(),
        "note": note,
        "decided_at": time.time(),
        "decided_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prev_hash": prev,
    }
    row["entry_hash"] = hashlib.sha256(
        (json.dumps(row, sort_keys=True) + prev).encode()
    ).hexdigest()

    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return True, f"{verb} recorded for {decision_id}"


def verify_chain() -> tuple[bool, str]:
    """Tamper detection: an edited or reordered approval breaks the chain."""
    rows = _read_jsonl(DECISIONS)
    prev = "GENESIS"
    for i, r in enumerate(rows):
        if r.get("prev_hash") != prev:
            return False, f"chain break at entry {i} ({r.get('decision_id')}): prev_hash mismatch"
        body = {k: v for k, v in r.items() if k != "entry_hash"}
        expect = hashlib.sha256((json.dumps(body, sort_keys=True) + body["prev_hash"]).encode()).hexdigest()
        if expect != r.get("entry_hash"):
            return False, f"chain break at entry {i} ({r.get('decision_id')}): entry_hash mismatch"
        prev = r["entry_hash"]
    return True, f"chain intact ({len(rows)} decisions)"
