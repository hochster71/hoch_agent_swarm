#!/usr/bin/env python3
"""Closed-loop ledger extended burn-in (methodology-stable operational evidence).

Does NOT change Mission Trace OBSERVE_ONLY or Phase 1 interface.

Workload dimensions (identical class to unit burn-in, scaled):
  - sequential growth to N appends (default 5000; env HELM_LEDGER_BURNIN_N)
  - multi-process contention (env HELM_LEDGER_BURNIN_PROCS / APPENDS)
  - integrity + deterministic replay
  - tamper / torn-line re-checks on copies (same fault classes)

Usage:
  python3 scripts/goal/run_closed_loop_ledger_burnin.py
  HELM_LEDGER_BURNIN_N=20000 python3 scripts/goal/run_closed_loop_ledger_burnin.py
"""
from __future__ import annotations

import json
import multiprocessing
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.helm_assurance_engine as eng  # noqa: E402


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


def main() -> int:
    n = int(os.environ.get("HELM_LEDGER_BURNIN_N", "5000"))
    n_procs = int(os.environ.get("HELM_LEDGER_BURNIN_PROCS", "16"))
    m_appends = int(os.environ.get("HELM_LEDGER_BURNIN_MP_APPENDS", "8"))

    print("FILESYSTEM_DEPLOYMENT_ASSUMPTIONS:")
    print(json.dumps(eng.FILESYSTEM_DEPLOYMENT_ASSUMPTIONS, indent=2))
    print()

    with tempfile.TemporaryDirectory(prefix="helm_ledger_burnin_") as td:
        td_path = Path(td)
        ledger = td_path / "burnin.jsonl"
        eng.CLOSED_LOOP_LEDGER_PATH = ledger

        t0 = time.perf_counter()
        for i in range(n):
            _append(f"SEQ{i}")
            if (i + 1) % max(1, n // 10) == 0:
                print(f"  growth {i+1}/{n}")
        t_seq = time.perf_counter() - t0

        integrity = eng.verify_closed_loop_ledger_integrity(ledger)
        replay = eng.replay_closed_loop_ledger(ledger)
        print(f"sequential: n={n} s={t_seq:.2f} integrity={integrity['status']} replay={replay['replay_status']}")
        if integrity["status"] != "VERIFIED_INTEGRITY" or replay["replay_status"] != "DETERMINISTIC_REPLAY_SUCCESS":
            return 1

        # Multi-process on a fresh ledger
        mp_ledger = td_path / "mp.jsonl"
        eng.CLOSED_LOOP_LEDGER_PATH = mp_ledger
        procs = [
            multiprocessing.Process(target=_mp_worker, args=(str(mp_ledger), i, m_appends))
            for i in range(n_procs)
        ]
        t1 = time.perf_counter()
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=300)
            if p.exitcode != 0:
                print(f"FAIL: process exit {p.exitcode}")
                return 1
        t_mp = time.perf_counter() - t1
        expected = n_procs * m_appends
        mi = eng.verify_closed_loop_ledger_integrity(mp_ledger)
        mr = eng.replay_closed_loop_ledger(mp_ledger)
        print(
            f"multiprocess: procs={n_procs} each={m_appends} expected={expected} "
            f"s={t_mp:.2f} integrity={mi['status']} replay={mr['replay_status']} "
            f"total={mi.get('total_transactions')}"
        )
        if mi["status"] != "VERIFIED_INTEGRITY" or mi.get("total_transactions") != expected:
            return 1

        # Fault re-check (same classes as unit burn-in) on sequential snapshot
        snap = ledger.read_text()
        torn = td_path / "torn.jsonl"
        torn.write_text(snap + '{"partial":true')
        ti = eng.verify_closed_loop_ledger_integrity(torn)
        print(f"torn_line: {ti['status']}")
        if ti["status"] != "MALFORMED_ENTRY":
            return 1

        tamp = td_path / "tamp.jsonl"
        lines = snap.splitlines()
        rec = json.loads(lines[-1])
        rec["current_transaction_hash"] = "f" * 64
        lines[-1] = json.dumps(rec)
        tamp.write_text("\n".join(lines) + "\n")
        ta = eng.verify_closed_loop_ledger_integrity(tamp)
        print(f"tampered_digest: {ta['status']} code={((ta.get('chain_error') or {}).get('code'))}")
        if ta["status"] != "HASH_CHAIN_BROKEN":
            return 1

        print("BURNIN_PASS")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
