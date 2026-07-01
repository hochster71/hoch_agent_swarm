#!/usr/bin/env python3
"""
scripts/seed_relay_accountability.py
=====================================
RC26: One-shot idempotent seed script for HAS-WORKER-RELAY-001 accountability entry.

Inserts HAS-WORKER-RELAY-001 into the agent_trust_scores table at a baseline
score of 80 (Tier 4: Trusted Autonomous). Safe to re-run — checks for existing
entry before inserting. Not a daemon.

Usage:
    python3 scripts/seed_relay_accountability.py

Exit codes:
    0 — success (inserted or already exists)
    1 — error
"""

from __future__ import annotations

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend is importable from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

RELAY_WORKER_ID = "HAS-WORKER-RELAY-001"
BASELINE_SCORE = 80
BASELINE_TIER = "GOLD"  # Tier 4: Trusted Autonomous (score >= 80)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def seed_relay_worker() -> int:
    """
    Seed HAS-WORKER-RELAY-001 into the accountability engine.
    Returns 0 on success, 1 on error.
    """
    try:
        from backend.mission_control.accountability_engine import (
            get_agent,
            get_all_agents,
        )
        from backend.runtime_truth.state_store import get_db_connection

        # Check if already seeded
        existing = get_agent(RELAY_WORKER_ID)
        if existing is not None:
            print(f"[SKIP] {RELAY_WORKER_ID} already exists in agent_trust_scores (score={existing.get('score', 'N/A')})")
            return 0

        # Insert baseline entry via direct DB write
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            # Determine table schema
            cur.execute("PRAGMA table_info(agent_trust_scores)")
            cols = [row[1] for row in cur.fetchall()]

            now = _now_iso()

            if "score" in cols and "tier" in cols:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO agent_trust_scores
                        (agent_id, score, tier, created_at, updated_at, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        RELAY_WORKER_ID,
                        BASELINE_SCORE,
                        BASELINE_TIER,
                        now,
                        now,
                        "RC26 seed: VPS relay worker hoch-relay-001. Baseline score 80 (Trusted Autonomous).",
                    ),
                )
                conn.commit()
                rows_inserted = cur.rowcount
                if rows_inserted > 0:
                    print(f"[OK] Seeded {RELAY_WORKER_ID}: score={BASELINE_SCORE}, tier={BASELINE_TIER}")
                else:
                    print(f"[SKIP] {RELAY_WORKER_ID} already present (INSERT OR IGNORE no-op)")
            else:
                print(f"[WARN] agent_trust_scores schema differs: cols={cols}")
                print("[WARN] Attempting minimal insert...")
                cur.execute(
                    "INSERT OR IGNORE INTO agent_trust_scores (agent_id) VALUES (?)",
                    (RELAY_WORKER_ID,),
                )
                conn.commit()
                print(f"[OK] Minimal seed inserted for {RELAY_WORKER_ID}")

        finally:
            conn.close()

        return 0

    except ImportError as exc:
        print(f"[ERROR] Import failed — run from repo root: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[ERROR] Seeding failed: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    print(f"RC26 Accountability Seed — {RELAY_WORKER_ID}")
    print(f"Baseline score: {BASELINE_SCORE}, tier: {BASELINE_TIER}")
    print("-" * 60)
    code = seed_relay_worker()
    print("-" * 60)
    if code == 0:
        print("[DONE] Seed complete. Re-running is safe (idempotent).")
    else:
        print("[FAILED] See errors above.")
    sys.exit(code)


if __name__ == "__main__":
    main()
