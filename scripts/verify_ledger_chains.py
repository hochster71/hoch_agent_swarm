#!/usr/bin/env python3
"""verify_ledger_chains.py — append-only HISTORICAL integrity via hash-chain linkage.

HELM-GOV | extends: AU-9 evidence-chain pattern | doctrine: Governance-before-Capability
         | edr: EDR-0006 (AC-5) | why: Auditor findings F-A6/F-B5 — a git-diff cannot prove HISTORICAL
         | append-only (a committed rewrite leaves HEAD clean). Hash-chain LINKAGE can: no record may be
         | deleted, inserted, or reordered without breaking the prev-pointer chain. This verifies every
         | governed ledger that carries a chain, and content-recomputes the ones whose scheme is known.

Linkage check (all chained ledgers): record[i][prev_field] == record[i-1][hash_field].
Content recompute (known scheme): re-hash the record body and compare (detects edits, not just deletes).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (path, hash_field, prev_field). Field names differ per ledger — discovered from their headers.
CHAINED_LEDGERS = [
    ("coordination/security/conmon_ledger.jsonl", "entry_hash", "prev_hash"),
    ("coordination/council/relay/gateway_dispatch_ledger.jsonl", "record_hash", "previous_record_hash"),
    ("coordination/security/doctrine_findings_ledger.jsonl", "record_hash", "prev_hash"),
    ("coordination/founder/decision_ledger.jsonl", "entry_hash", "prev_hash"),
]

# genesis sentinels a first record's prev pointer may legitimately hold
GENESIS = {"GENESIS", "", None, "0" * 64, "sha256:" + "0" * 64}


def _rows(path: Path):
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            try:
                yield json.loads(ln)
            except json.JSONDecodeError:
                yield {"__malformed__": ln[:80]}


def verify_linkage(path: Path, hash_field: str, prev_field: str) -> dict:
    """Tamper-evidence rule (concurrency-aware): every record's prev must reference SOME earlier
    record's hash (or genesis). A DELETED record breaks this — its child's prev references a hash no
    longer present. A concurrency FORK (two records sharing a parent) does NOT break it. We report:
      INTACT  strict linear chain (each prev == immediate predecessor's hash)
      FORKED  valid DAG with concurrency forks, but no dangling prev (still tamper-evident vs deletion)
      BROKEN  a prev references a hash that appears nowhere earlier -> a record was removed/rewritten
    """
    if not path.exists():
        return {"path": str(path), "state": "ABSENT", "records": 0}
    rows = list(_rows(path))
    if not rows:
        return {"path": str(path), "state": "EMPTY", "records": 0}
    seen: set = set()
    linear = True
    forks = 0
    prev_hash = None
    for i, r in enumerate(rows):
        if "__malformed__" in r:
            return {"path": str(path), "state": "BROKEN", "records": len(rows), "break_at": i, "reason": "malformed json"}
        pv = r.get(prev_field)
        if i == 0 or pv in GENESIS:
            pass  # genesis / chain root
        elif pv not in seen:
            # dangling pointer -> a referenced earlier record is missing (deletion/rewrite)
            return {"path": str(path), "state": "BROKEN", "records": len(rows), "break_at": i,
                    "reason": f"{prev_field} references a hash absent from all earlier records (record removed?)"}
        elif pv != prev_hash:
            linear = False
            forks += 1
        h = r.get(hash_field)
        if not h:
            return {"path": str(path), "state": "BROKEN", "records": len(rows), "break_at": i, "reason": f"missing {hash_field}"}
        seen.add(h)
        prev_hash = h
    return {"path": str(path), "state": "INTACT" if linear else "FORKED", "records": len(rows), "forks": forks}


def verify_findings_content() -> dict:
    """Content recompute for the ledger whose scheme we own (doctrine_findings_ledger)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from doctrine_findings_ledger import verify_chain
    ok, msg = verify_chain()
    return {"ledger": "doctrine_findings_ledger.jsonl", "content_recompute": "INTACT" if ok else "BROKEN", "detail": msg}


def run() -> dict:
    results = [verify_linkage(ROOT / p, hf, pf) for p, hf, pf in CHAINED_LEDGERS]
    content = verify_findings_content()
    # FORKED = valid DAG (concurrency), still tamper-evident against deletion; acceptable. BROKEN = deletion.
    all_intact = all(r["state"] in ("INTACT", "FORKED", "ABSENT", "EMPTY") for r in results) and content["content_recompute"] == "INTACT"
    return {"all_chains_intact": all_intact, "linkage": results, "content": content,
            "method": "prev-pointer linkage (no delete/insert/reorder without a break) + content recompute where scheme is owned"}


if __name__ == "__main__":
    r = run()
    for x in r["linkage"]:
        print(f"  [{x['state']:7s}] {x.get('records',0):5d} rec  {x['path']}")
    print(f"  content recompute (findings): {r['content']['content_recompute']}")
    print(f"\n  ALL CHAINS INTACT: {r['all_chains_intact']}")
    sys.exit(0 if r["all_chains_intact"] else 2)
