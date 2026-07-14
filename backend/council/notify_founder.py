"""Escalation delivery that needs NO CREDENTIALS. HELM reaches Michael; he stops polling.

Twilio SMS was the existing path and it is DEAD -- it needs TWILIO_ACCOUNT_SID / AUTH_TOKEN,
which is credential handling, which is FOUNDER_ONLY. A notification channel that cannot be
switched on without the founder's involvement does not reduce founder-minutes; it adds a
prerequisite.

These channels need nothing:
    MACOS   -- Notification Centre via osascript. Always available. Default.
    IMESSAGE-- sends to Michael's own Apple ID, reaches his iPhone. OPT-IN
               (HELM_NOTIFY_IMESSAGE=<his handle>), because sending a message is an act,
               and acts are opt-in even when the recipient is the owner.

RULES:
  * NEVER notify about something the system could prove itself. Escalation is for judgment.
  * DEDUPE. The same question must not buzz his phone twice. (A dedup key with a nonce in it
    does not dedup -- that bug already cost him 24 duplicate cards.)
  * NEVER put a secret in a notification. Notifications are stored, synced and previewed on a
    lock screen.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "coordination" / "founder" / "escalation_queue.jsonl"
SENT = ROOT / "coordination" / "founder" / "notifications_sent.jsonl"

SECRET_RX = re.compile(r"(sk_live\w*|sk_test\w*|whsec_\w*|service_role|Bearer\s+\S+|"
                       r"\b[0-9a-f]{32,}\b)", re.I)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sanitize(t: str) -> str:
    """A lock-screen preview is a public surface. Fail closed."""
    out = SECRET_RX.sub("<REDACTED>", t or "")
    assert not SECRET_RX.search(out), "notification sanitisation failed"
    return out


def _already_notified(key: str) -> bool:
    if not SENT.exists():
        return False
    for line in SENT.read_text().splitlines():
        try:
            if json.loads(line).get("dedup_key") == key:
                return True
        except json.JSONDecodeError:
            continue
    return False


def _record(key: str, channel: str, ok: bool, detail: str = "") -> None:
    SENT.parent.mkdir(parents=True, exist_ok=True)
    with open(SENT, "a", encoding="utf-8") as f:
        f.write(json.dumps({"dedup_key": key, "channel": channel, "ok": ok,
                            "detail": detail[:120], "at": _now()}) + "\n")


def _macos(title: str, body: str) -> tuple[bool, str]:
    """Notification Centre. No credentials, always available."""
    t = title.replace('"', "'")
    b = body.replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{b}" with title "{t}" sound name "Submarine"'],
            capture_output=True, timeout=10, check=True)
        return True, "macos notification delivered"
    except Exception as e:
        return False, f"macos notify failed: {str(e)[:80]}"


def _imessage(handle: str, body: str) -> tuple[bool, str]:
    """Reaches his iPhone. OPT-IN: sending a message is an act, even to yourself."""
    b = body.replace('"', "'")
    script = (f'tell application "Messages" to send "{b}" to '
              f'buddy "{handle}" of (1st service whose service type = iMessage)')
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            return True, "imessage delivered"
        return False, f"imessage failed: {(r.stderr or '')[:80]}"
    except Exception as e:
        return False, f"imessage error: {str(e)[:80]}"


def notify(esc: dict[str, Any]) -> dict[str, Any]:
    """Deliver ONE escalation. Deduped, sanitised, credential-free."""
    key = esc.get("dedup_key") or esc.get("decision_id") or ""
    if not key:
        return {"delivered": False, "reason": "no dedup key — refusing to risk a duplicate buzz"}
    if _already_notified(key):
        return {"delivered": False, "reason": f"DEDUP: already notified ({key}); "
                                              "the same question must not buzz twice"}

    q = _sanitize(str(esc.get("one_sentence_question", ""))[:120])
    why = _sanitize(str(esc.get("why_it_needs_you", ""))[:140])
    body = f"{q}\n{why}\nhttps://michaels-macbook-pro.tail826763.ts.net/founder"

    results = []
    ok_any = False

    ok, detail = _macos("HELM — decision needed", body)
    results.append({"channel": "macos", "ok": ok, "detail": detail})
    ok_any = ok_any or ok
    _record(key, "macos", ok, detail)

    handle = os.environ.get("HELM_NOTIFY_IMESSAGE", "").strip()
    if handle:
        ok, detail = _imessage(handle, f"HELM needs you:\n{body}")
        results.append({"channel": "imessage", "ok": ok, "detail": detail})
        ok_any = ok_any or ok
        _record(key, "imessage", ok, detail)

    return {"delivered": ok_any, "dedup_key": key, "channels": results}


def drain() -> dict[str, Any]:
    """Notify every UNNOTIFIED escalation in the queue. Idempotent — safe to run on a timer."""
    if not QUEUE.exists():
        return {"pending": 0, "notified": 0, "skipped": 0}
    rows = []
    for line in QUEUE.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    notified = skipped = 0
    for r in rows:
        res = notify(r)
        if res.get("delivered"):
            notified += 1
        else:
            skipped += 1
    return {"pending": len(rows), "notified": notified, "skipped": skipped, "at": _now()}


if __name__ == "__main__":
    print(json.dumps(drain(), indent=2))
