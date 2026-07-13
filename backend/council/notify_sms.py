"""notify_sms.py — deliver founder-contract escalations to Michael by SMS (Twilio).

AUTHORITY NOTE
--------------
The Twilio credentials are FOUNDER_ONLY (coordination/founder/authority_matrix.json). This
module NEVER holds or prints them — it reads them from the environment that Michael sets:

    TWILIO_ACCOUNT_SID   TWILIO_AUTH_TOKEN   TWILIO_FROM   FOUNDER_PHONE

If any are unset it does not send and does not crash — it records WOULD_SEND so the
autonomy layer keeps running and the escalation still lands in the queue file.

SAFETY RAILS (a notifier bug must never become a text storm)
  * RATE LIMIT: at most MAX_PER_HOUR texts/hour, enforced against a local ledger.
  * DEDUPE: the same decision_id is never texted twice.
  * SHAPE GATE: only a valid founder-contract escalation is sent; noise is dropped.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "coordination" / "founder" / "sms_ledger.jsonl"

MAX_PER_HOUR = 6            # a hard cap: a runaway loop cannot exceed this
DEDUPE_WINDOW_S = 86400     # never re-text the same decision within 24h


def _sent_recent() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    cutoff = time.time() - 3600
    for line in LEDGER.read_text().splitlines():
        try:
            d = json.loads(line)
            if d.get("ts", 0) >= cutoff:
                out.append(d)
        except json.JSONDecodeError:
            pass
    return out


def _already_sent(decision_id: str) -> bool:
    if not LEDGER.exists():
        return False
    cutoff = time.time() - DEDUPE_WINDOW_S
    for line in LEDGER.read_text().splitlines():
        try:
            d = json.loads(line)
            if d.get("decision_id") == decision_id and d.get("ts", 0) >= cutoff:
                return True
        except json.JSONDecodeError:
            pass
    return False


def _record(decision_id: str, status: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "decision_id": decision_id, "status": status}) + "\n")


def _compose(esc: dict) -> str:
    q = esc.get("one_sentence_question", "decision needed")
    why = esc.get("why_it_needs_you", "")
    opts = " / ".join(esc.get("options", [])[:2])
    return f"HELM: {q}\nWhy: {why}\nOptions: {opts}\nid={esc.get('decision_id','?')}"[:1000]


def notify(esc: dict) -> tuple[bool, str]:
    """Return (sent, status). Never raises. Never leaks a credential."""
    did = esc.get("decision_id", "")
    if not did or not esc.get("one_sentence_question"):
        return False, "DROPPED_INVALID_SHAPE"
    if _already_sent(did):
        return False, "SKIPPED_DEDUPE"
    if len(_sent_recent()) >= MAX_PER_HOUR:
        _record(did, "RATE_LIMITED")
        return False, "RATE_LIMITED"

    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    frm = os.environ.get("TWILIO_FROM", "").strip()
    to = os.environ.get("FOUNDER_PHONE", "").strip()
    if not all((sid, tok, frm, to)):
        _record(did, "WOULD_SEND_NOT_CONFIGURED")
        return False, "WOULD_SEND_NOT_CONFIGURED"

    body = urllib.parse.urlencode({"From": frm, "To": to, "Body": _compose(esc)}).encode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data=body, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode())
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = r.status in (200, 201)
        _record(did, "SENT" if ok else f"HTTP_{r.status}")
        return ok, "SENT" if ok else f"HTTP_{r.status}"
    except Exception as e:  # noqa: BLE001 — never let a notify failure stop the autonomy loop
        _record(did, "SEND_FAILED")
        return False, f"SEND_FAILED:{str(e)[:80]}"
