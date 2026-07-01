#!/usr/bin/env python3
"""
scripts/verify_doctrine_db.py
==============================
RC27: Verification script — confirms doctrine_rules table exists and is
functional in the backend swarm_ledger.db.

Checks:
  1. Database file exists.
  2. doctrine_rules table exists.
  3. All expected columns are present.
  4. SELECT from doctrine_rules executes without error.
  5. init_brain_tables() is idempotent (safe to re-run).

Usage:
    python3 scripts/verify_doctrine_db.py

Exit codes:
    0 — all checks pass
    1 — any check fails
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EXPECTED_COLUMNS = {"id", "rule_text", "source", "confidence", "active", "created_at"}


def _get_db_path() -> Path:
    import os
    env = os.getenv("HOCHSTER_DB_PATH")
    if env:
        return Path(env)
    if Path("/app").exists():
        return Path("/app/backend/swarm_ledger.db")
    return Path(__file__).resolve().parent.parent / "backend" / "swarm_ledger.db"


def _check(label: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def main() -> int:
    print("RC27 Doctrine DB Verification")
    print("-" * 56)

    db_path = _get_db_path()
    print(f"  DB path: {db_path}")
    all_pass = True

    # ── Check 1: DB file exists ──────────────────────────────────
    exists = db_path.exists()
    all_pass &= _check("DB file exists", exists, str(db_path))
    if not exists:
        print("\n[FAIL] Cannot continue — database does not exist.")
        return 1

    try:
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        all_pass &= _check("DB open", False, str(exc))
        return 1

    try:
        # ── Check 2: doctrine_rules table exists ─────────────────
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='doctrine_rules'"
        )
        table_exists = cur.fetchone() is not None
        all_pass &= _check("doctrine_rules table exists", table_exists)

        if not table_exists:
            print("\n[FAIL] doctrine_rules table missing — run the backend once to auto-create it.")
            return 1

        # ── Check 3: expected columns present ────────────────────
        cur2 = conn.execute("PRAGMA table_info(doctrine_rules)")
        actual_cols = {row["name"] for row in cur2.fetchall()}
        missing = EXPECTED_COLUMNS - actual_cols
        cols_ok = len(missing) == 0
        all_pass &= _check(
            "all expected columns present",
            cols_ok,
            f"actual={sorted(actual_cols)}" if cols_ok else f"missing={sorted(missing)}",
        )

        # ── Check 4: SELECT executes without error ────────────────
        try:
            cur3 = conn.execute(
                "SELECT id, rule_text, source, confidence, active, created_at "
                "FROM doctrine_rules WHERE active = 1"
            )
            rows = cur3.fetchall()
            all_pass &= _check("SELECT from doctrine_rules", True, f"rows={len(rows)}")
        except Exception as exc:
            all_pass &= _check("SELECT from doctrine_rules", False, str(exc))

        # ── Check 5: init_brain_tables is idempotent ─────────────
        try:
            from backend.brain.database import init_brain_tables
            init_brain_tables()
            # Verify table still exists after re-init
            cur4 = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='doctrine_rules'"
            )
            still_exists = cur4.fetchone() is not None
            all_pass &= _check(
                "init_brain_tables() idempotent (table survives re-run)",
                still_exists,
            )
        except Exception as exc:
            all_pass &= _check("init_brain_tables() idempotent", False, str(exc))

    finally:
        conn.close()

    print("-" * 56)
    if all_pass:
        print("[DONE] All checks passed — doctrine_rules is healthy.")
    else:
        print("[FAIL] One or more checks failed — see above.")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
