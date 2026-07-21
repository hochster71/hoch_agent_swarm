#!/usr/bin/env python3
"""Closed-loop ledger extended burn-in — operational characterization only.

Methodology is FROZEN. This run scales the same invariants; it does not invent
new workload logic.

Invariants (every checkpoint + end):
  - record count exact
  - deterministic replay
  - hash-chain continuity intact
  - malformed entries = 0
  - lock failures = 0
  - recovery events = 0 (clean sequential path)

Checkpoints (for N=20000 overnight default set):
  0 → 1000 → 5000 → 10000 → 15000 → 20000
(If HELM_LEDGER_BURNIN_N differs, all listed points ≤ N plus final N.)

Same fault classes after sequential (unchanged):
  multi-process contention, torn final line, tampered digest.

Does NOT change Mission Trace OBSERVE_ONLY or Phase 1 interface.

Usage:
  HELM_LEDGER_BURNIN_N=20000 HELM_LEDGER_BURNIN_PROCS=16 HELM_LEDGER_BURNIN_MP_APPENDS=10 \\
    python3 scripts/goal/run_closed_loop_ledger_burnin.py

  # Report path (JSON with provenance + checkpoint metrics):
  HELM_LEDGER_BURNIN_REPORT_DIR=coordination/governance/burnin_reports \\
    python3 scripts/goal/run_closed_loop_ledger_burnin.py
"""
from __future__ import annotations

import json
import multiprocessing
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.helm_assurance_engine as eng  # noqa: E402

# Fixed checkpoint schedule for overnight N=20000 (methodology identity).
FIXED_CHECKPOINTS = (0, 1000, 5000, 10000, 15000, 20000)


def _append(worker: str) -> None:
    eng.append_closed_loop_ledger_entry(
        worker_id=worker,
        evaluation_digest_sha256="d" * 64,
        graph_manifest_sha256="g" * 64,
        policy_version="2.2",
        reasoning_model="2.2",
        canonicalization={"spec": "RFC8785"},
        produced_artifacts=[],
        refreshed_telemetry=[],
        previous_confidence_score=0.1,
        new_confidence_score=0.2,
        previous_status="REDUCED",
        new_status="REDUCED",
        evidence_snapshot=["E1"],
        technical_authorization={"ok": True},
        operational_authorization={"ok": False},
    )


def _mp_worker(ledger: str, wid: int, m: int) -> None:
    eng.CLOSED_LOOP_LEDGER_PATH = Path(ledger)
    for j in range(m):
        _append(f"MP{wid}-A{j}")


def _git_full_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def _cpu_model() -> str:
    try:
        if platform.system() == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            return out or platform.processor() or "UNKNOWN"
        if Path("/proc/cpuinfo").is_file():
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or platform.machine() or "UNKNOWN"


def _memory_bytes() -> Optional[int]:
    try:
        if platform.system() == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            return int(out)
        if Path("/proc/meminfo").is_file():
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    # kB
                    return int(line.split()[1]) * 1024
    except Exception:
        pass
    return None


def _filesystem_type(path: Path) -> str:
    """Best-effort local FS type (APFS/ext4/…)."""
    try:
        if platform.system() == "Darwin":
            # df -T not portable on macOS; use diskutil on volume of path
            resolved = path.resolve()
            out = subprocess.check_output(
                ["df", str(resolved)],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            # Fall through to mount table
            mnt = subprocess.check_output(["mount"], text=True, stderr=subprocess.DEVNULL)
            # Prefer path containing resolved root
            for line in mnt.splitlines():
                if " on / " in line or " on /System/Volumes/Data " in line:
                    if "apfs" in line.lower():
                        return "apfs"
            if "apfs" in mnt.lower():
                return "apfs"
            return "macos-unknown"
        # Linux
        out = subprocess.check_output(
            ["df", "-T", str(path.resolve())],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        lines = out.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 2:
                return parts[1]
    except Exception:
        pass
    return "UNKNOWN"


def capture_provenance(params: Dict[str, Any]) -> Dict[str, Any]:
    mem = _memory_bytes()
    return {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": _git_full_sha(),  # full 40-char when available
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "os": platform.system(),
        "os_version": platform.mac_ver()[0] or platform.version(),
        "platform": platform.platform(),
        "filesystem": _filesystem_type(ROOT),
        "cpu_model": _cpu_model(),
        "memory_bytes": mem,
        "memory_gib": round(mem / (1024**3), 2) if mem else None,
        "hostname": platform.node(),
        "burnin_parameters": params,
        "filesystem_deployment_assumptions": eng.FILESYSTEM_DEPLOYMENT_ASSUMPTIONS,
        "methodology": {
            "note": "Workload identity frozen — same invariants as unit burn-in, scaled.",
            "invariants": [
                "record_count_exact",
                "deterministic_replay",
                "chain_continuity_intact",
                "malformed_entries_0",
                "lock_failures_0",
                "recovery_events_0_on_clean_path",
            ],
            "fault_classes_unchanged": [
                "multiprocess_contention",
                "partial_final_line",
                "tampered_digest",
            ],
        },
    }


def checkpoint_verify(
    ledger: Path,
    *,
    expected_count: int,
    lock_failures: int,
    recovery_events: int,
) -> Dict[str, Any]:
    """Run the same invariant suite at a growth checkpoint."""
    t0 = time.perf_counter()
    integrity = eng.verify_closed_loop_ledger_integrity(ledger)
    t_integrity = time.perf_counter() - t0

    t1 = time.perf_counter()
    replay = eng.replay_closed_loop_ledger(ledger)
    t_replay = time.perf_counter() - t1

    parse_errors = integrity.get("parse_errors") or []
    malformed = len(parse_errors)
    chain_ok = bool(integrity.get("chain_verified"))
    record_count = int(integrity.get("total_transactions") or 0)

    status_ok = (
        integrity.get("status") == "VERIFIED_INTEGRITY"
        and replay.get("replay_status") == "DETERMINISTIC_REPLAY_SUCCESS"
        and record_count == expected_count
        and chain_ok
        and malformed == 0
        and lock_failures == 0
        and recovery_events == 0
        and int(replay.get("total_chained_transactions") or -1) == expected_count
    )

    return {
        "expected_record_count": expected_count,
        "record_count": record_count,
        "record_count_exact": record_count == expected_count,
        "replay_status": replay.get("replay_status"),
        "replay_deterministic": replay.get("replay_status") == "DETERMINISTIC_REPLAY_SUCCESS",
        "chain_continuity": chain_ok,
        "integrity_status": integrity.get("status"),
        "malformed_entries": malformed,
        "lock_failures": lock_failures,
        "recovery_events": recovery_events,
        "integrity_duration_s": round(t_integrity, 6),
        "replay_duration_s": round(t_replay, 6),
        "ok": status_ok,
        "metrics_table": {
            "Record count": "Exact" if record_count == expected_count else f"FAIL got {record_count}",
            "Replay": "Deterministic" if replay.get("replay_status") == "DETERMINISTIC_REPLAY_SUCCESS" else "FAIL",
            "Chain continuity": "Intact" if chain_ok else "FAIL",
            "Malformed entries": malformed,
            "Lock failures": lock_failures,
            "Recovery events": recovery_events,
            "Replay duration_s": round(t_replay, 6),
        },
    }


def resolve_checkpoints(n: int) -> List[int]:
    """Fixed schedule capped to N; always include 0 and final N."""
    pts = [c for c in FIXED_CHECKPOINTS if c <= n]
    if 0 not in pts:
        pts.insert(0, 0)
    if n not in pts:
        pts.append(n)
    return sorted(set(pts))


def main() -> int:
    n = int(os.environ.get("HELM_LEDGER_BURNIN_N", "5000"))
    n_procs = int(os.environ.get("HELM_LEDGER_BURNIN_PROCS", "16"))
    m_appends = int(os.environ.get("HELM_LEDGER_BURNIN_MP_APPENDS", "8"))
    report_dir = Path(
        os.environ.get(
            "HELM_LEDGER_BURNIN_REPORT_DIR",
            str(ROOT / "coordination" / "governance" / "burnin_reports"),
        )
    )

    params = {
        "HELM_LEDGER_BURNIN_N": n,
        "HELM_LEDGER_BURNIN_PROCS": n_procs,
        "HELM_LEDGER_BURNIN_MP_APPENDS": m_appends,
        "checkpoints": resolve_checkpoints(n),
    }
    provenance = capture_provenance(params)

    print("=== BURN-IN PROVENANCE ===")
    print(json.dumps({k: provenance[k] for k in (
        "captured_at", "git_commit", "python_version", "os", "os_version",
        "filesystem", "cpu_model", "memory_gib", "burnin_parameters",
    )}, indent=2))
    print()
    print("FILESYSTEM_DEPLOYMENT_ASSUMPTIONS:")
    print(json.dumps(eng.FILESYSTEM_DEPLOYMENT_ASSUMPTIONS, indent=2))
    print()

    checkpoints = resolve_checkpoints(n)
    report: Dict[str, Any] = {
        "schema": "HELM_CLOSED_LOOP_LEDGER_BURNIN_v1",
        "result": "RUNNING",
        "provenance": provenance,
        "sequential_checkpoints": [],
        "multiprocess": None,
        "fault_rechecks": {},
    }

    lock_failures = 0
    recovery_events = 0  # clean sequential path must stay 0

    with tempfile.TemporaryDirectory(prefix="helm_ledger_burnin_") as td:
        td_path = Path(td)
        ledger = td_path / "burnin.jsonl"
        eng.CLOSED_LOOP_LEDGER_PATH = ledger

        # Checkpoint 0 (empty ledger)
        cp0 = checkpoint_verify(
            ledger,
            expected_count=0,
            lock_failures=lock_failures,
            recovery_events=recovery_events,
        )
        # Empty ledger is EMPTY_LEDGER / NO_LEDGER — special-case expected
        if not ledger.exists() or ledger.stat().st_size == 0:
            cp0 = {
                "expected_record_count": 0,
                "record_count": 0,
                "record_count_exact": True,
                "replay_status": "NO_LEDGER_OR_EMPTY",
                "replay_deterministic": True,
                "chain_continuity": True,
                "integrity_status": "EMPTY_AT_START",
                "malformed_entries": 0,
                "lock_failures": 0,
                "recovery_events": 0,
                "integrity_duration_s": 0.0,
                "replay_duration_s": 0.0,
                "ok": True,
                "metrics_table": {
                    "Record count": "Exact",
                    "Replay": "N/A empty",
                    "Chain continuity": "Intact",
                    "Malformed entries": 0,
                    "Lock failures": 0,
                    "Recovery events": 0,
                    "Replay duration_s": 0.0,
                },
            }
        report["sequential_checkpoints"].append({"at": 0, **cp0})
        print(f"checkpoint @0: ok={cp0['ok']} metrics={cp0['metrics_table']}")
        if not cp0["ok"]:
            report["result"] = "FAIL_CHECKPOINT_0"
            return _write_report(report_dir, report, 1)

        written = 0
        t_seq0 = time.perf_counter()
        last_cp_time = t_seq0
        append_latencies_ms: List[float] = []

        for target in checkpoints:
            if target == 0:
                continue
            while written < target:
                t_a0 = time.perf_counter()
                try:
                    _append(f"SEQ{written}")
                except Exception as e:
                    lock_failures += 1
                    print(f"FAIL: append error at {written}: {e}")
                    report["result"] = "FAIL_APPEND"
                    report["append_error"] = str(e)
                    report["lock_failures"] = lock_failures
                    return _write_report(report_dir, report, 1)
                append_latencies_ms.append((time.perf_counter() - t_a0) * 1000.0)
                written += 1

            cp = checkpoint_verify(
                ledger,
                expected_count=target,
                lock_failures=lock_failures,
                recovery_events=recovery_events,
            )
            since = time.perf_counter() - last_cp_time
            last_cp_time = time.perf_counter()
            # Latency since previous checkpoint (batch of appends)
            batch = append_latencies_ms[-max(1, target - (checkpoints[checkpoints.index(target) - 1] if target in checkpoints else target)):] if append_latencies_ms else []
            # Simpler: appends from previous checkpoint to now
            prev_at = 0
            for c in checkpoints:
                if c < target:
                    prev_at = c
            batch_n = target - prev_at
            batch_lat = append_latencies_ms[-batch_n:] if batch_n <= len(append_latencies_ms) else append_latencies_ms
            cp["segment_wall_s"] = round(since, 4)
            cp["append_latency_ms_avg"] = round(sum(batch_lat) / len(batch_lat), 4) if batch_lat else None
            cp["append_latency_ms_p50"] = round(sorted(batch_lat)[len(batch_lat) // 2], 4) if batch_lat else None
            cp["append_latency_ms_max"] = round(max(batch_lat), 4) if batch_lat else None
            cp["throughput_appends_per_s"] = round(batch_n / since, 2) if since > 0 else None

            report["sequential_checkpoints"].append({"at": target, **cp})
            print(
                f"checkpoint @{target}: ok={cp['ok']} "
                f"replay_s={cp['replay_duration_s']} "
                f"append_avg_ms={cp['append_latency_ms_avg']} "
                f"tps={cp['throughput_appends_per_s']} "
                f"table={cp['metrics_table']}"
            )
            if not cp["ok"]:
                report["result"] = f"FAIL_CHECKPOINT_{target}"
                report["lock_failures"] = lock_failures
                report["recovery_events"] = recovery_events
                return _write_report(report_dir, report, 1)

        t_seq = time.perf_counter() - t_seq0
        report["sequential_summary"] = {
            "n": n,
            "wall_s": round(t_seq, 4),
            "append_latency_ms_avg": round(sum(append_latencies_ms) / len(append_latencies_ms), 4) if append_latencies_ms else None,
            "append_latency_ms_max": round(max(append_latencies_ms), 4) if append_latencies_ms else None,
            "throughput_appends_per_s": round(n / t_seq, 2) if t_seq > 0 else None,
            "lock_failures": lock_failures,
            "recovery_events": recovery_events,
        }
        print(f"sequential complete: {report['sequential_summary']}")

        # --- multi-process (same methodology class; fresh ledger) ---
        mp_ledger = td_path / "mp.jsonl"
        eng.CLOSED_LOOP_LEDGER_PATH = mp_ledger
        expected_mp = n_procs * m_appends
        procs = [
            multiprocessing.Process(target=_mp_worker, args=(str(mp_ledger), i, m_appends))
            for i in range(n_procs)
        ]
        t1 = time.perf_counter()
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=600)
            if p.exitcode != 0:
                report["result"] = "FAIL_MULTIPROCESS"
                report["multiprocess"] = {"exitcode": p.exitcode}
                return _write_report(report_dir, report, 1)
        t_mp = time.perf_counter() - t1
        mi = eng.verify_closed_loop_ledger_integrity(mp_ledger)
        mr = eng.replay_closed_loop_ledger(mp_ledger)
        mp_ok = (
            mi.get("status") == "VERIFIED_INTEGRITY"
            and mi.get("total_transactions") == expected_mp
            and mi.get("chain_verified") is True
            and not (mi.get("parse_errors") or [])
            and mr.get("replay_status") == "DETERMINISTIC_REPLAY_SUCCESS"
            and mr.get("total_chained_transactions") == expected_mp
        )
        report["multiprocess"] = {
            "procs": n_procs,
            "appends_each": m_appends,
            "expected": expected_mp,
            "wall_s": round(t_mp, 4),
            "integrity_status": mi.get("status"),
            "replay_status": mr.get("replay_status"),
            "total_transactions": mi.get("total_transactions"),
            "chain_verified": mi.get("chain_verified"),
            "malformed_entries": len(mi.get("parse_errors") or []),
            "ok": mp_ok,
        }
        print(f"multiprocess: {report['multiprocess']}")
        if not mp_ok:
            report["result"] = "FAIL_MULTIPROCESS"
            return _write_report(report_dir, report, 1)

        # --- fault re-checks (same classes; copies of sequential snapshot) ---
        snap = ledger.read_text()
        torn = td_path / "torn.jsonl"
        torn.write_text(snap + '{"partial":true')
        ti = eng.verify_closed_loop_ledger_integrity(torn)
        torn_ok = ti.get("status") == "MALFORMED_ENTRY"
        report["fault_rechecks"]["torn_line"] = {
            "status": ti.get("status"),
            "ok": torn_ok,
            "expected": "MALFORMED_ENTRY",
        }
        print(f"torn_line: {report['fault_rechecks']['torn_line']}")
        if not torn_ok:
            report["result"] = "FAIL_TORN"
            return _write_report(report_dir, report, 1)

        tamp = td_path / "tamp.jsonl"
        lines = snap.splitlines()
        rec = json.loads(lines[-1])
        rec["current_transaction_hash"] = "f" * 64
        lines[-1] = json.dumps(rec)
        tamp.write_text("\n".join(lines) + "\n")
        ta = eng.verify_closed_loop_ledger_integrity(tamp)
        tamp_ok = (
            ta.get("status") == "HASH_CHAIN_BROKEN"
            and (ta.get("chain_error") or {}).get("code") == "HASH_COMPUTATION_MISMATCH"
        )
        report["fault_rechecks"]["tampered_digest"] = {
            "status": ta.get("status"),
            "code": (ta.get("chain_error") or {}).get("code"),
            "ok": tamp_ok,
            "expected": "HASH_CHAIN_BROKEN / HASH_COMPUTATION_MISMATCH",
        }
        print(f"tampered_digest: {report['fault_rechecks']['tampered_digest']}")
        if not tamp_ok:
            report["result"] = "FAIL_TAMPER"
            return _write_report(report_dir, report, 1)

        report["result"] = "BURNIN_PASS"
        report["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print("BURNIN_PASS")
        return _write_report(report_dir, report, 0)


def _write_report(report_dir: Path, report: Dict[str, Any], code: int) -> int:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = (report.get("provenance") or {}).get("git_commit", "UNKNOWN")[:12]
    path = report_dir / f"burnin_{ts}_{sha}_{report.get('result', 'UNKNOWN')}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"report: {path}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
