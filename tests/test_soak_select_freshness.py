"""Soak package selection must not resurrect a DEAD false-start. Test before the fix.

DEFECT (2026-07-14): after Phase A sealed PASS, the wall/API's /chain endpoint showed CONTRADICTED
because select_soak_package() returned an ABANDONED earlier false-start (soak_runner died mid-run,
never wrote a terminal status, so its last snapshot said IN_PROGRESS forever). Its chain was a broken
72-row stub — a false-red shown as if it were the live truth, while the real sealed Phase A package
(1668-row intact chain) was ignored.

A dead soak is not 'in progress'. An IN_PROGRESS snapshot from a process that stopped writing hours ago
is abandoned. Selection must prefer the latest SEALED package over a stale unsealed one.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from backend.truth import soak_select as S


def _pkg(root: Path, name: str) -> Path:
    p = root / name
    (p / "daemon").mkdir(parents=True)
    return p


def _snapshot(pkg: Path, status: str, age_seconds: float):
    f = pkg / "runtime_truth_snapshots.jsonl"
    f.write_text(json.dumps({"soak_status": status}) + "\n")
    (pkg / "soak_config.json").write_text(json.dumps({"started_at": "2026-07-14T20:38:35Z"}))
    old = time.time() - age_seconds
    os.utime(f, (old, old))
    for d in (pkg / "daemon").glob("*"):
        os.utime(d, (old, old))


def _seal(pkg: Path, verdict: str, sealed_at: str):
    (pkg / "seal_verdict.json").write_text(json.dumps({"verdict": verdict, "sealed_at": sealed_at}))
    (pkg / "soak_config.json").write_text(json.dumps({"started_at": "2026-07-14T20:47:15Z"}))
    led = pkg / "daemon" / "task_lease_ledger.jsonl"
    led.write_text("\n".join(json.dumps({"i": i}) for i in range(1668)) + "\n")


def test_abandoned_in_progress_false_start_is_not_selected_over_sealed(tmp_path):
    dead = _pkg(tmp_path, "HELM-SOAK-2H-20260714T203835Z")   # the real false-start id
    _snapshot(dead, "IN_PROGRESS", age_seconds=6 * 3600)     # snapshot says live, but 6h stale = DEAD
    live = _pkg(tmp_path, "HELM-SOAK-2H-20260714T204715Z")   # the real sealed Phase A id
    _seal(live, "SOAK_PHASE_A_PASS", "2026-07-14T22:49:21Z")

    chosen = S.select_soak_package(tmp_path)
    assert chosen is not None and chosen.name.endswith("204715Z"), (
        f"selected the abandoned false-start instead of the sealed Phase A: {chosen}")


def test_a_genuinely_fresh_in_progress_package_is_still_selected(tmp_path):
    """The fix must not break the normal case: a soak writing RIGHT NOW is in progress and wins."""
    running = _pkg(tmp_path, "HELM-SOAK-8H-20260714T230000Z")
    _snapshot(running, "IN_PROGRESS", age_seconds=5)         # fresh — actively writing
    sealed = _pkg(tmp_path, "HELM-SOAK-2H-20260714T204715Z")
    _seal(sealed, "SOAK_PHASE_A_PASS", "2026-07-14T22:49:21Z")

    chosen = S.select_soak_package(tmp_path)
    assert chosen is not None and chosen.name.endswith("230000Z"), (
        "a genuinely live soak must be selected over an older sealed phase")


def test_freshness_helper_is_honest(tmp_path):
    p = _pkg(tmp_path, "HELM-SOAK-2H-20260714T204715Z")
    f = p / "daemon" / "x.jsonl"; f.write_text("{}\n")
    assert S._fresh(p) is True
    old = time.time() - 4000
    os.utime(f, (old, old))
    assert S._fresh(p) is False, "stale evidence must read as NOT fresh"
