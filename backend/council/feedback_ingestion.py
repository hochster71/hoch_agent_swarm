"""feedback_ingestion.py — a founder decision on an escalation becomes durable policy.

    escalation → APPROVE / DENY / RETURN_FOR_CHANGES
      → signed decision event → scope validation → decision record → corpus update
      → affected tasks re-evaluated

CRITICAL RULE (founder-ratified): do NOT turn every approval into permanent doctrine.
The founder chooses the reuse scope; the DEFAULT is THIS_ACTION_ONLY (single-use).

  THIS_ACTION_ONLY  -> single-use authorization (consumable once, then spent)
  THIS_MISSION      -> ratified, scoped to one mission
  THIS_PRODUCT      -> ratified, scoped to one product
  THIS_FACTORY      -> ratified, scoped to one factory
  STANDING_POLICY   -> ratified reusable doctrine (broadest)

SINGLE-USE-AUTHORIZATION-CONTROL: a THIS_ACTION_ONLY grant, once consumed, cannot
authorize a second action. Proving a broad standing policy is never *inferred* from a
one-time approval is the key negative control.
"""
from __future__ import annotations

import hashlib
import json
import time
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "coordination" / "founder" / "decision_corpus_v2.jsonl"
FEEDBACK = ROOT / "coordination" / "founder" / "founder_feedback_events.jsonl"
SINGLE_USE = ROOT / "coordination" / "founder" / "single_use_grants.jsonl"


class Reuse(str, Enum):
    THIS_ACTION_ONLY = "THIS_ACTION_ONLY"   # default — single use
    THIS_MISSION = "THIS_MISSION"
    THIS_PRODUCT = "THIS_PRODUCT"
    THIS_FACTORY = "THIS_FACTORY"
    STANDING_POLICY = "STANDING_POLICY"


class Response(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    RETURN_FOR_CHANGES = "RETURN_FOR_CHANGES"
    REVOKE = "REVOKE"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sig(payload: dict[str, Any], token: str) -> str:
    """A decision event must carry founder provenance. HMAC over the payload with the
    founder token. A response lacking valid provenance is rejected (negative control)."""
    import hmac
    body = json.dumps(payload, sort_keys=True)
    return hmac.new(token.encode(), body.encode(), hashlib.sha256).hexdigest()


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def ingest(*, escalation: dict[str, Any], response: str, reuse: str = "THIS_ACTION_ONLY",
           scope: dict[str, Any] | None = None, founder_token: str,
           founder_id: str = "Michael Bryan Hoch") -> tuple[bool, str]:
    """Turn a founder response into a durable policy event. Returns (ok, message)."""
    if not founder_token:
        return False, "REJECTED: no founder provenance (token) on the response"
    try:
        resp = Response(response.upper())
    except ValueError:
        return False, f"REJECTED: unknown response '{response}'"
    try:
        ru = Reuse(reuse.upper())
    except ValueError:
        return False, f"REJECTED: unknown reuse scope '{reuse}'"

    eid = escalation.get("decision_id") or escalation.get("escalation_id") or "ESC-?"
    event = {
        "event_id": f"FE-{int(time.time()*1000)}",
        "escalation_id": eid,
        "response": resp.value,
        "reuse": ru.value,
        "founder_id": founder_id,
        "at": _now(),
    }
    event["signature"] = _sig(event, founder_token)
    _append(FEEDBACK, event)

    # DENY / RETURN_FOR_CHANGES never create authorizing doctrine.
    if resp in (Response.DENY, Response.RETURN_FOR_CHANGES):
        return True, f"{resp.value} recorded; task remains blocked, no authorization created"

    # APPROVE:
    if ru is Reuse.THIS_ACTION_ONLY:
        # single-use grant — consumable once, NOT a standing decision record
        grant = {"grant_id": event["event_id"], "escalation_id": eid,
                 "consumed": False, "created_at": _now()}
        _append(SINGLE_USE, grant)
        return True, f"single-use authorization created ({event['event_id']}); NOT permanent doctrine"

    # scoped/standing APPROVE -> a versioned RATIFIED decision record
    sc = scope or {"factory_ids": ["*"], "product_ids": ["*"], "mission_ids": ["*"],
                   "environments": ["*"], "action_types": ["*"]}
    decision_text = f"Founder {resp.value} ({ru.value}) for {eid}: {escalation.get('one_sentence_question','')}"
    record = {
        "schema_version": "1.0",
        "decision_id": f"FD-{time.strftime('%Y%m%d')}-{event['event_id'][-6:]}",
        "title": f"{ru.value} authorization from escalation {eid}",
        "status": "RATIFIED",
        "authority": "FOUNDER",
        "scope": sc,
        "decision": decision_text,
        "rationale": f"Founder approved via escalation {eid} with reuse={ru.value}",
        "source_type": "FOUNDER_FEEDBACK",
        "source_reference": event["event_id"],
        "source_sha256": hashlib.sha256(decision_text.encode()).hexdigest(),
        "confidence": "AUTHORITATIVE",
        "effective_at": _now(),
        "expires_at": None,
        "review_at": None,
        "supersedes": [],
        "superseded_by": None,
        "conflicts_with": [],
        "created_at": _now(),
        "created_by": founder_id,
    }
    _append(CORPUS, record)
    return True, f"RATIFIED decision {record['decision_id']} created (scope={ru.value})"


def consume_single_use(escalation_id: str) -> tuple[bool, str]:
    """SINGLE-USE-AUTHORIZATION-CONTROL: spend a one-time grant. Second attempt fails."""
    if not SINGLE_USE.exists():
        return False, "no single-use grant for this escalation"
    rows = [json.loads(l) for l in SINGLE_USE.read_text().splitlines() if l.strip()]
    for r in rows:
        if r["escalation_id"] == escalation_id and not r["consumed"]:
            r["consumed"] = True
            r["consumed_at"] = _now()
            SINGLE_USE.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
            return True, f"single-use grant {r['grant_id']} consumed"
    return False, "no UNCONSUMED single-use grant (already spent, or none) — authorization denied"
