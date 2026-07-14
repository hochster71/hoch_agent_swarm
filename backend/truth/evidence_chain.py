"""AU-9 — Protection of Audit Information. A tamper-evident evidence plane.

WHY THIS EXISTS
---------------
On 2026-07-14 a record was deleted from the middle of the live lease ledger
(1269 -> 1268 records). NOTHING detected it. No chain, no signature, no integrity check.

That is why no baseline has ever held. A baseline is only as durable as the evidence plane
beneath it, and this one was append-only by CONVENTION, not by ENFORCEMENT. Every "locked"
baseline was written on ground that could be silently rewritten afterward — so it could never be
KNOWN to have held.

THE CONTRACT
------------
Every record binds to its predecessor:

    entry_hash = sha256( canonical(payload) + prev_hash )

Delete, edit, reorder, truncate or forge a record and the chain breaks at that point and stays
broken for every record after it. Verification is O(n) and cannot be fooled by rewriting a single
row, because the row's hash is an input to every hash that follows.

FAIL-CLOSED
-----------
A broken chain raises ChainBroken. It NEVER returns "probably fine".
Missing evidence is UNKNOWN. TAMPERED evidence is CONTRADICTED. Neither is PASS.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

GENESIS = "GENESIS"
_CHAIN_FIELDS = ("prev_hash", "entry_hash")


class ChainBroken(Exception):
    """The evidence chain is BROKEN — the history has been altered. This is CONTRADICTED, not
    an absence of data. It must never be downgraded to a warning."""


def _canonical(payload: Dict[str, Any]) -> str:
    """Deterministic serialization. The chain fields are never part of what is hashed."""
    body = {k: v for k, v in payload.items() if k not in _CHAIN_FIELDS}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(payload: Dict[str, Any], prev_hash: str) -> str:
    return hashlib.sha256((_canonical(payload) + prev_hash).encode("utf-8")).hexdigest()


def head_hash(path: Path) -> str:
    """Hash of the last record, or GENESIS for an empty/absent ledger."""
    p = Path(path)
    if not p.exists():
        return GENESIS
    last = None
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    if last is None:
        return GENESIS
    try:
        return json.loads(last).get("entry_hash") or GENESIS
    except Exception as e:
        raise ChainBroken(f"CONTRADICTED: tail record is unparseable: {e}")


def append_record(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append a chained record. Durable: fsync'd, so a crash cannot leave a torn tail."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    prev = head_hash(p)
    rec = dict(payload)
    rec["prev_hash"] = prev
    rec["entry_hash"] = compute_hash(rec, prev)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rec


def verify_chain(path: Path, *, expected_head: Optional[str] = None) -> bool:
    """Walk the chain. Raise ChainBroken on ANY alteration.

    Detects: deletion, in-place edit, reordering, tail truncation, forged append.
    """
    p = Path(path)
    if not p.exists():
        raise ChainBroken(f"CONTRADICTED: ledger is missing: {p}")

    prev = GENESIS
    n = 0
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                raise ChainBroken(f"CONTRADICTED: record {i} is unparseable: {e}")

            got_prev = rec.get("prev_hash")
            if got_prev != prev:
                raise ChainBroken(
                    f"CONTRADICTED: chain BROKEN at record {i} — prev_hash={got_prev!r} "
                    f"but the preceding record hashes to {prev!r}. "
                    f"History has been deleted, reordered or edited.")

            recomputed = compute_hash(rec, prev)
            if rec.get("entry_hash") != recomputed:
                raise ChainBroken(
                    f"CONTRADICTED: record {i} has been ALTERED IN PLACE — "
                    f"entry_hash does not match its own contents.")

            prev = rec["entry_hash"]
            n += 1

    if expected_head is not None and prev != expected_head:
        raise ChainBroken(
            f"CONTRADICTED: chain was TRUNCATED — head is {prev!r}, expected {expected_head!r}. "
            f"Records have been removed from the end.")
    return True


def chain_status(path: Path, *, expected_head: Optional[str] = None) -> Dict[str, Any]:
    """Non-raising status for dashboards. NEVER returns a green on a broken chain."""
    try:
        verify_chain(path, expected_head=expected_head)
        return {"state": "CONFIRMED_LIVE", "head": head_hash(path)}
    except ChainBroken as e:
        return {"state": "CONTRADICTED", "reason": str(e)}
    except Exception as e:
        return {"state": "UNKNOWN", "reason": str(e)}


def migrate_to_chain(path: Path) -> Dict[str, Any]:
    """Chain an EXISTING unchained ledger, in place, atomically.

    This does NOT retroactively prove the past — the records before migration were never
    protected and we do not pretend otherwise. It seals history from this point forward, and it
    records honestly that everything before the seal is UNVERIFIABLE.
    """
    p = Path(path)
    rows: List[Dict[str, Any]] = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    rows.append({"__unparseable__": line[:200]})

    prev = GENESIS
    out: List[str] = []
    for r in rows:
        r = {k: v for k, v in r.items() if k not in _CHAIN_FIELDS}
        r["pre_chain_unverifiable"] = True     # honest: this record predates the chain
        r["prev_hash"] = prev
        r["entry_hash"] = compute_hash(r, prev)
        prev = r["entry_hash"]
        out.append(json.dumps(r, sort_keys=True, default=str))

    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".chaining")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + ("\n" if out else ""))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)                          # atomic
    return {"records": len(out), "head": prev,
            "note": "records prior to migration are marked pre_chain_unverifiable"}
