#!/usr/bin/env python3
"""LIVE restart-recovery proof (HH-4).

Replaces the previous artifact, which was three hardcoded literals
(`expired_leases_detected: 1`, `recovered_lease_ids: ["lease-stale-test"]`,
`recovery_status: "SUCCESS"`) and demonstrated no process interruption at all.

This performs a REAL crash/recovery cycle and records only OBSERVED values:

  1. spawn a real worker process that acquires a REAL lease (fencing token N)
     and then hangs, holding the lease;
  2. capture PID / heartbeat / active leases BEFORE;
  3. SIGKILL it  -- an uncatchable crash, no cleanup, lease left orphaned;
  4. capture exit status and confirm the PID is gone;
  5. restart: a NEW worker attempts the SAME task. The lease manager must
     detect the orphaned/expired lock, recover it, and mint a STRICTLY GREATER
     fencing token (N+1) -- proving the dead process can never act again;
  6. capture leases AFTER, recovered vs abandoned task ids, duplicate-execution
     count, and the scheduler cycle after recovery.

Any field that cannot be observed is emitted as UNKNOWN and the artifact is
downgraded to STRUCTURAL_PROOF. LIVE_RUNTIME_PROOF is emitted ONLY when every
required field was actually measured.
"""
from __future__ import annotations

import datetime
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

REQUIRED_FIELDS = [
    "service_pid_before", "service_pid_after", "restart_command", "exit_status",
    "heartbeat_before", "heartbeat_after", "active_leases_before",
    "active_leases_after", "duplicate_execution_count", "recovered_task_ids",
    "abandoned_task_ids", "fencing_token_before", "fencing_token_after",
    "fencing_monotonic", "scheduler_cycle_after_recovery",
]

TASK_ID = "T-RESTART-RECOVERY-PROOF"
LEASE_SECONDS = 2  # short so the orphaned lock genuinely expires post-crash

# The child: acquires a REAL lease, records it, then hangs forever holding it.
CHILD = r"""
import json, sys, time
sys.path.insert(0, {root!r})
from scripts.ag_execution_lease_manager import LeaseManager
lm = LeaseManager()
lease = lm.acquire_lease({task!r}, holder="restart-proof-worker", duration_seconds={secs})
print(json.dumps({{"pid": __import__("os").getpid(), "lease": lease}}), flush=True)
# Hold the lease and hang. We will be SIGKILLed -- no cleanup, no release.
while True:
    time.sleep(0.2)
"""


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def active_leases():
    from scripts.ag_execution_lease_manager import LEASES_FILE
    try:
        data = json.loads(Path(LEASES_FILE).read_text())
    except Exception:
        return []
    return [l for l in data if l.get("status") in (None, "ACTIVE", "ACQUIRED")]


def max_token():
    from scripts.ag_execution_lease_manager import LEASES_FILE
    try:
        data = json.loads(Path(LEASES_FILE).read_text())
    except Exception:
        return 0
    return max([l.get("fencing_token", 0) for l in data] or [0])


def _read_json_line(proc, timeout=15.0):
    """The lease manager prints human notices to stdout; skip to the JSON line."""
    import time as _t
    deadline = _t.time() + timeout
    while _t.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                continue
    return None


def main() -> int:
    obs: dict = {"schema": "RESTART_RECOVERY_PROOF_v2", "observed_at_utc": now(),
                 "task_id": TASK_ID}

    # ---------------- BEFORE ----------------
    obs["heartbeat_before"] = now()
    obs["active_leases_before"] = active_leases()
    token_before_env = max_token()

    src = CHILD.format(root=str(ROOT), task=TASK_ID, secs=LEASE_SECONDS)
    proc = subprocess.Popen([sys.executable, "-c", src], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
    child = _read_json_line(proc)
    if not child:
        err = proc.stderr.read()[:400]
        print(f"child failed to acquire lease: {err}", file=sys.stderr)
        proc.kill()
        return 2
    obs["service_pid_before"] = child["pid"]
    obs["fencing_token_before"] = child["lease"]["fencing_token"]
    obs["lease_id_before"] = child["lease"]["lease_id"]
    obs["active_leases_before"] = active_leases()

    # ---------------- CRASH (uncatchable) ----------------
    obs["restart_command"] = f"SIGKILL {child['pid']} -> respawn worker for {TASK_ID}"
    os.kill(child["pid"], signal.SIGKILL)
    proc.wait(timeout=10)
    obs["exit_status"] = proc.returncode          # -9 == killed by SIGKILL
    obs["killed_by_signal"] = (proc.returncode == -signal.SIGKILL)
    time.sleep(0.2)
    obs["pid_before_alive_after_kill"] = pid_alive(child["pid"])

    # let the orphaned lease actually expire
    time.sleep(LEASE_SECONDS + 0.5)

    # ---------------- RESTART / RECOVERY ----------------
    src2 = CHILD.format(root=str(ROOT), task=TASK_ID, secs=60)
    proc2 = subprocess.Popen([sys.executable, "-c", src2], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
    child2 = _read_json_line(proc2)
    recovered, abandoned = [], []
    if child2:
        obs["service_pid_after"] = child2["pid"]
        obs["fencing_token_after"] = child2["lease"]["fencing_token"]
        obs["lease_id_after"] = child2["lease"]["lease_id"]
        recovered = [TASK_ID]
    else:
        obs["service_pid_after"] = None
        obs["fencing_token_after"] = None
        abandoned = [TASK_ID]
    proc2.kill(); proc2.wait(timeout=10)

    obs["heartbeat_after"] = now()
    obs["active_leases_after"] = active_leases()
    obs["recovered_task_ids"] = recovered
    obs["abandoned_task_ids"] = abandoned

    # Fencing: the new token MUST strictly exceed the dead holder's token, so a
    # resurrected/zombie writer can never win a write.
    tb, ta = obs.get("fencing_token_before"), obs.get("fencing_token_after")
    obs["fencing_monotonic"] = bool(tb is not None and ta is not None and ta > tb)
    obs["fencing_token_env_max_before"] = token_before_env

    # Duplicate execution: the same task must never hold two ACTIVE leases.
    dupes = [l for l in obs["active_leases_after"] if l.get("task_id") == TASK_ID]
    obs["duplicate_execution_count"] = max(0, len(dupes) - 1)

    # ---------------- scheduler cycle after recovery ----------------
    try:
        from backend.mission_control.persistent_scheduler import PersistentScheduler
        cyc = PersistentScheduler(evidence_dir=ROOT / "coordination" / "council").run_once()
        obs["scheduler_cycle_after_recovery"] = cyc
    except Exception as e:
        obs["scheduler_cycle_after_recovery"] = {"state": "UNKNOWN", "error": str(e)[:160]}

    # ---------------- classify honestly ----------------
    missing = [f for f in REQUIRED_FIELDS
               if obs.get(f) is None
               or (isinstance(obs.get(f), dict) and obs[f].get("state") == "UNKNOWN")]
    live_ok = (
        not missing
        and obs["killed_by_signal"]
        and obs["pid_before_alive_after_kill"] is False
        and obs["fencing_monotonic"]
        and obs["duplicate_execution_count"] == 0
        and obs["recovered_task_ids"] == [TASK_ID]
    )
    obs["missing_fields"] = missing
    obs["proof_class"] = "LIVE_RUNTIME_PROOF" if live_ok else "STRUCTURAL_PROOF"
    obs["recovery_status"] = "SUCCESS" if live_ok else "NOT_PROVEN"
    obs["notes"] = (
        "All values OBSERVED from a real SIGKILL of a real lease-holding process. "
        "No literal was written without measurement."
        if live_ok else
        "Downgraded: one or more required fields could not be observed. "
        "This is NOT live runtime proof."
    )

    out = ROOT / "coordination" / "council" / "restart_recovery_proof.json"
    out.write_text(json.dumps(obs, indent=2) + "\n")
    print(json.dumps({k: obs[k] for k in (
        "proof_class", "recovery_status", "service_pid_before", "service_pid_after",
        "exit_status", "killed_by_signal", "fencing_token_before",
        "fencing_token_after", "fencing_monotonic", "duplicate_execution_count",
        "recovered_task_ids", "abandoned_task_ids", "missing_fields")}, indent=2))
    return 0 if obs["proof_class"] == "LIVE_RUNTIME_PROOF" else 1


if __name__ == "__main__":
    raise SystemExit(main())
