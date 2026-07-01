#!/usr/bin/env python3
"""
scripts/seed_relay_accountability.py
=====================================
RC26: One-shot idempotent seed script for HAS-WORKER-RELAY-001 accountability entry.

Inserts HAS-WORKER-RELAY-001 into agent_trust_scores at a baseline
score of 80 (Tier 4: Trusted Autonomous / GOLD). Safe to re-run —
checks for existing entry before inserting (INSERT OR IGNORE).

Usage:
    python3 scripts/seed_relay_accountability.py

Exit codes:
    0 — success (inserted or already exists)
    1 — error
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the repo root is on sys.path so backend imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RELAY_WORKER_ID   = "HAS-WORKER-RELAY-001"
BASELINE_SCORE    = 80
BASELINE_TIER     = "GOLD"       # score >= 80  →  Tier 4: Trusted Autonomous
BASELINE_BAND     = "TRUSTED"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _get_db_path() -> Path:
    """
    Mirror the exact DB path resolution used by
    backend.runtime_truth.state_store — env var first, then
    /app path if running in Docker, else repo-relative.
    """
    import os
    env = os.getenv("HOCHSTER_DB_PATH")
    if env:
        return Path(env)
    if Path("/app").exists():
        return Path("/app/backend/swarm_ledger.db")
    # Repo-relative: backend/swarm_ledger.db
    return Path(__file__).resolve().parent.parent / "backend" / "swarm_ledger.db"


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA synchronous=NORMAL;")


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def seed_relay_worker() -> int:
    """
    Seed HAS-WORKER-RELAY-001 into agent_trust_scores.
    Returns 0 on success, 1 on error.
    """
    db_path = _get_db_path()
    print(f"DB path: {db_path}")

    if not db_path.exists():
        print(f"[ERROR] Database not found at {db_path}", file=sys.stderr)
        print("[ERROR] Start the backend at least once to create the DB, then re-run.", file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        _apply_pragmas(conn)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        print(f"[ERROR] Cannot open DB: {exc}", file=sys.stderr)
        return 1

    try:
        # ── 1. Ensure table exists (idempotent) ───────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_trust_scores (
                agent_id              TEXT PRIMARY KEY,
                agent_name            TEXT NOT NULL,
                trust_score           INTEGER NOT NULL,
                trust_tier            TEXT NOT NULL,
                band                  TEXT NOT NULL,
                routing_priority      REAL NOT NULL,
                autonomy_budget       TEXT NOT NULL,
                allowed_actions       TEXT NOT NULL,
                restricted_actions    TEXT NOT NULL,
                score_dimensions      TEXT NOT NULL,
                reason                TEXT,
                required_remedy       TEXT,
                updated_at            TEXT NOT NULL
            )
        """)
        conn.commit()

        # ── 2. Check if already seeded ────────────────────────────────────────
        existing = conn.execute(
            "SELECT agent_id, trust_score, trust_tier FROM agent_trust_scores WHERE agent_id = ?",
            (RELAY_WORKER_ID,)
        ).fetchone()

        if existing is not None:
            print(
                f"[SKIP] {RELAY_WORKER_ID} already exists "
                f"(trust_score={existing['trust_score']}, tier={existing['trust_tier']})"
            )
            return 0

        # ── 3. Inspect actual columns to handle schema drift safely ───────────
        actual_cols = _get_columns(conn, "agent_trust_scores")
        print(f"Schema columns: {actual_cols}")

        # ── 4. Build insert using only columns that exist ─────────────────────
        now = _now_iso()

        # Required baseline values keyed by column name
        candidate = {
            "agent_id":           RELAY_WORKER_ID,
            "agent_name":         "Relay Worker (hoch-relay-001)",
            "trust_score":        BASELINE_SCORE,
            "trust_tier":         BASELINE_TIER,
            "band":               BASELINE_BAND,
            "routing_priority":   0.5,
            "autonomy_budget":    json.dumps({"relay": 5, "heartbeat": 100}),
            "allowed_actions":    json.dumps(["relay_forward", "heartbeat", "api"]),
            "restricted_actions": json.dumps([
                "compute", "governance_db_access", "prompt_approval",
                "pii_processing", "arbitrary_code_execution"
            ]),
            "score_dimensions":   json.dumps({
                "task_completion": 0.85,
                "accuracy": 0.80,
                "policy_compliance": 0.95,
                "security": 0.90,
                "penalties": 0
            }),
            "reason":             "RC26 seed: VPS relay worker hoch-relay-001. Baseline score 80 (Trusted Autonomous / GOLD).",
            "required_remedy":    None,
            "updated_at":         now,
            # Legacy optional columns — included only if schema has them
            "score":              BASELINE_SCORE,
            "tier":               BASELINE_TIER,
            "created_at":         now,
            "notes":              "RC26 seed: relay worker baseline.",
        }

        # Filter to columns that actually exist in this DB
        cols   = [c for c in actual_cols if c in candidate]
        values = [candidate[c] for c in cols]

        placeholders = ", ".join("?" * len(cols))
        col_names    = ", ".join(cols)

        conn.execute(
            f"INSERT OR IGNORE INTO agent_trust_scores ({col_names}) VALUES ({placeholders})",
            values,
        )
        conn.commit()

        # Verify insertion
        inserted = conn.execute(
            "SELECT agent_id, trust_score, trust_tier FROM agent_trust_scores WHERE agent_id = ?",
            (RELAY_WORKER_ID,)
        ).fetchone()

        if inserted is None:
            print(f"[ERROR] INSERT OR IGNORE completed but row not found — possible PK conflict.", file=sys.stderr)
            return 1

        print(
            f"[OK] Seeded {RELAY_WORKER_ID}: "
            f"trust_score={inserted['trust_score']}, tier={inserted['trust_tier']}"
        )
        return 0

    except Exception as exc:
        print(f"[ERROR] Seeding failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


def main() -> None:
    print(f"RC26 Accountability Seed — {RELAY_WORKER_ID}")
    print(f"Baseline: trust_score={BASELINE_SCORE}, tier={BASELINE_TIER}, band={BASELINE_BAND}")
    print("-" * 64)
    code = seed_relay_worker()
    print("-" * 64)
    if code == 0:
        print("[DONE] Seed complete. Re-running is safe (idempotent).")
    else:
        print("[FAILED] See errors above.")
    sys.exit(code)


if __name__ == "__main__":
    main()
