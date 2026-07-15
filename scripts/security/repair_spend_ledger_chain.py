#!/usr/bin/env python3
"""AU-9 recovery: linearize spend_ledger after concurrent-write forks.

History: before exclusive flock on append, concurrent writers forked prev_hash
links (same prev on two rows). This script:

  1. Archives the original ledger bytes (forensic, untouched)
  2. Rebuilds a linear hash chain from observed business fields
  3. Writes a recovery attestation JSON (not a green claim — a repair record)

Does NOT invent cost rows. Does NOT delete the archive.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "coordination" / "council" / "spend_ledger.jsonl"
ARCHIVE_DIR = ROOT / "coordination" / "council" / "ledger_archives"
EVIDENCE = ROOT / "docs" / "evidence" / "security" / "au9_spend_chain_recovery.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not LEDGER.exists():
        print("NO_LEDGER")
        return 1

    raw = LEDGER.read_text(encoding="utf-8")
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = ARCHIVE_DIR / f"spend_ledger.pre_au9_repair_{ts}.jsonl"
    shutil.copy2(LEDGER, archive)
    archive_hash = _sha256_file(archive)

    # Detect fork count under old chain rules
    prev = "GENESIS"
    forks = 0
    for i, e in enumerate(rows):
        if e.get("prev_hash") != prev:
            forks += 1
        prev = e.get("entry_hash") or ""

    rebuilt = []
    prev_hash = "GENESIS"
    for e in rows:
        body = {k: v for k, v in e.items() if k not in ("prev_hash", "entry_hash")}
        body["prev_hash"] = prev_hash
        body["entry_hash"] = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()
        ).hexdigest()
        rebuilt.append(body)
        prev_hash = body["entry_hash"]

    # Append recovery seal as final observed administrative row
    seal = {
        "ts": _now(),
        "task_id": "AU9-SPEND-CHAIN-RECOVERY",
        "adapter": "HELM_INTERNAL",
        "cost_usd": 0.0,
        "cost_state": "OBSERVED",
        "measurement": "CHAIN_RECOVERY",
        "note": (
            f"Linearized {len(rebuilt)} historical spend rows after concurrent-write forks. "
            f"Original archived sha256={archive_hash}"
        ),
        "archive_path": str(archive.relative_to(ROOT)),
        "forks_detected_before_repair": forks,
    }
    seal["prev_hash"] = prev_hash
    seal["entry_hash"] = hashlib.sha256(
        json.dumps(seal, sort_keys=True).encode()
    ).hexdigest()
    rebuilt.append(seal)

    tmp = LEDGER.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rebuilt:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    tmp.replace(LEDGER)

    # Verify
    from backend.mission_control.spend_meter import SpendMeter

    ok, bad = SpendMeter().verify_chain()
    evidence = {
        "schema": "AU9_SPEND_CHAIN_RECOVERY_v1",
        "repaired_at": _now(),
        "rows_rebuilt": len(rebuilt) - 1,
        "forks_detected_before_repair": forks,
        "archive_path": str(archive.relative_to(ROOT)),
        "archive_sha256": archive_hash,
        "chain_valid_after": ok,
        "residual_errors": bad[:10],
        "doctrine": (
            "Historical cost amounts preserved; prev_hash/entry_hash recomputed to restore "
            "tamper-evidence after concurrent writers forked the chain pre-flock. "
            "Original bytes retained in archive."
        ),
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "forks": forks, "archive": str(archive), "evidence": str(EVIDENCE)}))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
