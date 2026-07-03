#!/usr/bin/env python3
"""Founder-only CLI: approve or reject a pending approval with a signature.

Usage:
  python3 scripts/founder_approve.py <approval_id> approve|reject [note]

Signing prompts for the founder key passphrase (~/.has_founder/founder_signing_key).
Writes the signed decision to artifacts/approvals/decisions/ and updates queue.json.
Agents cannot replicate this without the passphrase.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.mission_control.founder_signer import sign_approval, verify_approval  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
QUEUE = REPO / "artifacts" / "approvals" / "queue.json"
DECISIONS = REPO / "artifacts" / "approvals" / "decisions"
KEY = Path.home() / ".has_founder" / "founder_signing_key"


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[2] not in ("approve", "reject"):
        print(__doc__)
        return 2
    approval_id, action = sys.argv[1], sys.argv[2]
    note = sys.argv[3] if len(sys.argv) > 3 else ""
    if not KEY.exists():
        print(f"No founder key at {KEY}. Run scripts/founder_keygen.sh first.")
        return 1

    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    approvals = data.get("approvals", [])
    target = next((a for a in approvals if a.get("approval_id") == approval_id), None)
    if target is None:
        print(f"approval_id {approval_id} not found in queue.")
        return 1

    target["status"] = "APPROVED" if action == "approve" else "REJECTED"
    target["decision_at"] = datetime.now(timezone.utc).isoformat()
    target["decision_note"] = note
    target["decision_by"] = "Michael Hoch"

    signature = sign_approval(target, KEY)  # passphrase prompt happens here
    target["founder_signature"] = signature
    if not verify_approval(target, signature):
        print("Self-verification FAILED — decision not recorded.")
        return 1

    DECISIONS.mkdir(parents=True, exist_ok=True)
    (DECISIONS / f"decision_{approval_id}.json").write_text(
        json.dumps(target, indent=2), encoding="utf-8")
    QUEUE.write_text(json.dumps({"approvals": approvals}, indent=2), encoding="utf-8")
    print(f"{target['status']}: {approval_id} — signed and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
