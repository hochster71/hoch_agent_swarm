#!/usr/bin/env python3
"""Seed FOUR REAL bounded factory missions (RMF-2).

Fixes the root cause found by the eligibility ledger:

  The old seeder declared its OWN `CREATE TABLE IF NOT EXISTS mission_control_tasks`
  with column order (task_id, mission_id, step_index, name, assigned_agent, status, ...).
  The table already existed with (task_id, mission_id, name, assigned_agent, status,
  step_index, ...), so the CREATE was a no-op -- the real schema won -- but the seeder
  still INSERTed POSITIONALLY against its assumed order. Every value landed one column
  off: `status` received the AGENT NAME ("AgentHASF"), `step_index` received the literal
  string "PENDING". The scheduler filters `status IN ('PENDING','FAILED')`, so all four
  tasks were permanently INVISIBLE and dispatched_count was always 0.

  THE FIX: always INSERT with an EXPLICIT column list. Never positional VALUES against
  an assumed schema.

The four missions are real, bounded, and locally executable (LOCAL_ONLY adapter ->
zero credentials, zero spend).
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "backend" / "swarm_ledger.db"

SUBJECT_MODULE = "backend/mission_control/factory_validators.py"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


MISSIONS = [
    {
        "mission_id": "M-HASF-REAL-01", "factory": "HASF",
        "name": "Inspect a backend module and report concrete defects",
        "task_id": "T-HASF-REAL-01",
        "prompt": (
            "You are a senior Python reviewer. Review the module "
            f"`{SUBJECT_MODULE}`, whose purpose is to independently validate artifacts "
            "produced by AI factory agents.\n\n"
            "Produce a short defect report in markdown with:\n"
            "1. Two or three CONCRETE weaknesses or risks in a validator that checks "
            "AI output using regular expressions and length thresholds.\n"
            "2. For each, a specific recommended improvement.\n"
            "Be concrete and technical. Do not restate the prompt."
        ),
        "validator_ctx": {"subject": SUBJECT_MODULE},
    },
    {
        "mission_id": "M-HRF-REAL-01", "factory": "HRF",
        "name": "Cited technical comparison",
        "task_id": "T-HRF-REAL-01",
        "prompt": (
            "Write a concise technical comparison of two lease-coordination approaches "
            "for distributed workers: FENCING TOKENS versus TIME-BASED LEASE EXPIRY.\n\n"
            "Requirements:\n"
            "- Explicitly discuss BOTH 'fencing tokens' and 'lease expiry'.\n"
            "- Explain how each behaves when a worker is paused or crashes.\n"
            "- Use explicit comparison language (whereas / unlike / however).\n"
            "- State which is safer against a zombie writer, and why."
        ),
        "validator_ctx": {"compare": ["fencing", "lease expiry"]},
    },
    {
        "mission_id": "M-HCF-REAL-01", "factory": "HCF",
        "name": "Control-to-evidence gap analysis",
        "task_id": "T-HCF-REAL-01",
        "prompt": (
            "Perform a control-to-evidence gap analysis for an autonomous agent platform.\n\n"
            "Controls in scope:\n"
            "  C1 every model dispatch passes through a single governed gateway\n"
            "  C2 no task executes twice (duplicate-execution prevention)\n"
            "  C3 spend is capped per task\n"
            "  C4 evidence is bound to the exact commit under test\n\n"
            "For EACH control, state: the control, what EVIDENCE would prove it, and "
            "whether a GAP exists if that evidence is missing. Explicitly use the words "
            "control, evidence, and gap. Output markdown."
        ),
        "validator_ctx": {},
    },
    {
        "mission_id": "M-HSF-REAL-01", "factory": "HSF",
        "name": "Bounded creative artifact with deterministic package validation",
        "task_id": "T-HSF-REAL-01",
        "prompt": (
            "Write a SHORT poem, at least 6 non-empty lines, on the theme: "
            "'evidence'.\n\n"
            "Constraints (these are checked mechanically):\n"
            "- At least 6 non-empty lines.\n"
            "- The word 'evidence' must appear literally in the text.\n"
            "Output only the poem."
        ),
        "validator_ctx": {"min_lines": 6, "theme": "evidence"},
    },
]


def main() -> int:
    if not DB.exists():
        print(f"task DB missing: {DB}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(DB))
    try:
        # Carry the real mission instruction + validator context on the task row.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(mission_control_tasks)")}
        if "mission_prompt" not in cols:
            conn.execute("ALTER TABLE mission_control_tasks ADD COLUMN mission_prompt TEXT")
        if "validator_ctx" not in cols:
            conn.execute("ALTER TABLE mission_control_tasks ADD COLUMN validator_ctx TEXT")

        for m in MISSIONS:
            # EXPLICIT column lists -- the fix for the misalignment defect.
            conn.execute(
                "INSERT OR REPLACE INTO mission_control_missions "
                "(mission_id, name, target_pod, command, status, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (m["mission_id"], m["name"], m["factory"],
                 f"factory:{m['factory']}", "PENDING", now(), now()),
            )
            conn.execute(
                "INSERT OR REPLACE INTO mission_control_tasks "
                "(task_id, mission_id, name, assigned_agent, status, step_index, "
                " dependencies, error_message, evidence_path, created_at, updated_at, "
                " mission_prompt, validator_ctx) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (m["task_id"], m["mission_id"], m["name"], f"Agent{m['factory']}",
                 "PENDING",                      # <-- a real status, in the real column
                 1, "", "", "", now(), now(),
                 m["prompt"], json.dumps(m["validator_ctx"])),
            )
        conn.commit()

        rows = list(conn.execute(
            "SELECT task_id, status, step_index, assigned_agent FROM mission_control_tasks "
            "WHERE task_id LIKE 'T-%-REAL-%'"))
    finally:
        conn.close()

    seeded = [{"task_id": r[0], "status": r[1], "step_index": r[2], "assigned_agent": r[3]}
              for r in rows]
    out = ROOT / "coordination" / "council" / "seeded_missions.json"
    out.write_text(json.dumps({
        "schema": "SEEDED_MISSIONS_v1",
        "seeded_at_utc": now(),
        "fix": "INSERT with EXPLICIT column list (was: positional VALUES against an assumed schema)",
        "adapter_policy": "LOCAL_ONLY (ollama) -- zero credentials, zero spend",
        "missions": [{k: v for k, v in m.items() if k != "prompt"} for m in MISSIONS],
        "verified_rows": seeded,
    }, indent=2) + "\n")

    print(json.dumps({"seeded": seeded}, indent=2))
    ok = all(r["status"] == "PENDING" for r in seeded) and len(seeded) == 4
    print("STATUS COLUMN CORRECT:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
