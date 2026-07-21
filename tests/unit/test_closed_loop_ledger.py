"""Closed-loop ledger: locked append, hash-chain integrity, malformed-line handling.

Burn-in hardening for scripts/helm_assurance_engine.py (not Phase 1 mission trace).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

import scripts.helm_assurance_engine as eng


@pytest.fixture
def ledger_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "closed_loop_execution_ledger.jsonl"
    monkeypatch.setattr(eng, "CLOSED_LOOP_LEDGER_PATH", path)
    return path


def _append(worker: str = "W") -> dict:
    return eng.append_closed_loop_ledger_entry(
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


def test_append_serializes_prev_hash_under_lock(ledger_path: Path):
    a = _append("A")
    b = _append("B")
    assert b["previous_transaction_hash"] == a["current_transaction_hash"]
    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "VERIFIED_INTEGRITY"
    assert integrity["chain_verified"] is True
    assert integrity["total_transactions"] == 2


def test_integrity_detects_hash_chain_break(ledger_path: Path):
    _append("A")
    _append("B")
    lines = ledger_path.read_text().splitlines()
    # Corrupt second record's previous hash
    rec = json.loads(lines[1])
    rec["previous_transaction_hash"] = "DEADBEEF" * 8
    lines[1] = json.dumps(rec)
    ledger_path.write_text("\n".join(lines) + "\n")
    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "HASH_CHAIN_BROKEN"
    assert integrity["chain_verified"] is False
    assert integrity["chain_error"]["code"] == "HASH_CHAIN_DISCONTINUITY"


def test_integrity_detects_hash_recompute_mismatch(ledger_path: Path):
    _append("A")
    lines = ledger_path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["current_transaction_hash"] = "0" * 64
    ledger_path.write_text(json.dumps(rec) + "\n")
    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "HASH_CHAIN_BROKEN"
    assert integrity["chain_error"]["code"] == "HASH_COMPUTATION_MISMATCH"


def test_malformed_final_line_structured_error(ledger_path: Path):
    _append("A")
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write('{"transaction_id": "TX-TRUNCATED", "partial": true')  # no closing brace / newline end
    # integrity must not raise JSONDecodeError
    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "MALFORMED_ENTRY"
    assert integrity["parse_errors"]
    assert integrity["parse_errors"][0]["code"] == "MALFORMED_JSONL_LINE"
    assert integrity["parse_errors"][0].get("is_final_line") is True

    replay = eng.replay_closed_loop_ledger(ledger_path)
    assert replay["replay_status"] == "MALFORMED_ENTRY"
    assert replay["parse_errors"]


def test_load_fail_closed_raises_structured(ledger_path: Path):
    ledger_path.write_text("{not-json\n", encoding="utf-8")
    with pytest.raises(eng.ClosedLoopLedgerError) as ei:
        eng.load_closed_loop_ledger_records(ledger_path, fail_on_malformed=True)
    assert ei.value.code == "MALFORMED_JSONL_LINE"
    d = ei.value.to_dict()
    assert "line_number" in d


def test_concurrent_appends_preserve_chain(ledger_path: Path):
    """Multiple threads append; chain must remain continuous under flock."""
    errors: list = []
    results: list = []

    def worker(name: str) -> None:
        try:
            results.append(_append(name))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(f"T{i}",)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(results) == 8
    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "VERIFIED_INTEGRITY", integrity
    assert integrity["total_transactions"] == 8
    assert integrity["chain_verified"] is True

    replay = eng.replay_closed_loop_ledger(ledger_path)
    assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
    assert replay["total_chained_transactions"] == 8


@pytest.mark.parametrize("n_writers,m_appends", [(8, 10), (16, 8)])
def test_concurrent_writers_stress_nm(ledger_path: Path, n_writers: int, m_appends: int):
    """N concurrent writers × M appends each — regression for flock protocol.

    Verifies: expected record count, uninterrupted hash chain, deterministic
    replay, unique transaction_ids, continuous prev→curr links (no gaps/forks).
    All writers must honor the same locking protocol (fcntl/flock sidecar).
    """
    expected = n_writers * m_appends
    errors: list = []
    barrier = threading.Barrier(n_writers)

    def worker(wid: int) -> None:
        try:
            barrier.wait(timeout=30)
            for j in range(m_appends):
                _append(f"W{wid}-A{j}")
        except Exception as e:
            errors.append((wid, e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)

    assert not errors, errors

    lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == expected, f"expected {expected} records, got {len(lines)}"

    records = [json.loads(ln) for ln in lines]
    tx_ids = [r["transaction_id"] for r in records]
    assert len(tx_ids) == len(set(tx_ids)), "duplicate transaction_id"

    # Continuous chain positions: each prev must equal prior curr (or GENESIS for first)
    prev = "GENESIS_ROOT"
    for i, r in enumerate(records):
        assert r["previous_transaction_hash"] == prev, f"gap/fork at index {i}"
        prev = r["current_transaction_hash"]

    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "VERIFIED_INTEGRITY", integrity
    assert integrity["total_transactions"] == expected
    assert integrity["chain_verified"] is True
    assert integrity["chained_transactions"] == expected

    replay = eng.replay_closed_loop_ledger(ledger_path)
    assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
    assert replay["total_chained_transactions"] == expected
    assert replay["head_transaction_hash"] == records[-1]["current_transaction_hash"]


def test_burnin_workload_identity_growth_and_faults(ledger_path: Path, tmp_path: Path, monkeypatch):
    """Re-run the same burn-in dimensions (methodology frozen; only impl changes).

    Workload identity (do not change without new baseline):
      growth 1→10→100→500, restart replay, concurrent writers,
      partial final line, tampered digest, broken chain.
    """
    # --- growth stages (cumulative ledger) ---
    stages = [1, 10, 100, 500]
    written = 0
    for target in stages:
        while written < target:
            _append(f"G{written}")
            written += 1
        integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
        assert integrity["status"] == "VERIFIED_INTEGRITY", f"growth@{target}: {integrity}"
        assert integrity["total_transactions"] == target
        replay = eng.replay_closed_loop_ledger(ledger_path)
        assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
        assert replay["total_chained_transactions"] == target

    # --- restart replay (reload path, no rewrite) ---
    snapshot = ledger_path.read_bytes()
    monkeypatch.setattr(eng, "CLOSED_LOOP_LEDGER_PATH", ledger_path)
    replay2 = eng.replay_closed_loop_ledger(ledger_path)
    assert replay2["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
    assert ledger_path.read_bytes() == snapshot, "restart rewrote ledger history"

    # --- concurrent writers (same methodology class as stress) ---
    # Separate ledger so growth baseline remains clean for fault injection copies
    conc_path = tmp_path / "concurrent.jsonl"
    monkeypatch.setattr(eng, "CLOSED_LOOP_LEDGER_PATH", conc_path)
    n, m = 8, 5
    errs: list = []

    def cw(i: int) -> None:
        try:
            for j in range(m):
                _append(f"C{i}-{j}")
        except Exception as e:
            errs.append(e)

    ts = [threading.Thread(target=cw, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errs
    ci = eng.verify_closed_loop_ledger_integrity(conc_path)
    assert ci["status"] == "VERIFIED_INTEGRITY" and ci["total_transactions"] == n * m

    # Restore growth ledger for fault cases
    monkeypatch.setattr(eng, "CLOSED_LOOP_LEDGER_PATH", ledger_path)

    # --- partial final line ---
    torn = tmp_path / "torn.jsonl"
    torn.write_bytes(snapshot)
    with torn.open("a", encoding="utf-8") as f:
        f.write('{"transaction_id":"TX-TORN","partial":true')
    torn_i = eng.verify_closed_loop_ledger_integrity(torn)
    assert torn_i["status"] == "MALFORMED_ENTRY"
    assert torn_i["parse_errors"][0]["code"] == "MALFORMED_JSONL_LINE"

    # --- tampered digest (hash recompute fails) ---
    tamp = tmp_path / "tamp.jsonl"
    tamp.write_bytes(snapshot)
    lines = tamp.read_text().splitlines()
    rec = json.loads(lines[-1])
    rec["current_transaction_hash"] = "f" * 64
    lines[-1] = json.dumps(rec)
    tamp.write_text("\n".join(lines) + "\n")
    ti = eng.verify_closed_loop_ledger_integrity(tamp)
    assert ti["status"] == "HASH_CHAIN_BROKEN"
    assert ti["chain_error"]["code"] == "HASH_COMPUTATION_MISMATCH"

    # --- broken chain (discontinuity) ---
    brk = tmp_path / "broken.jsonl"
    brk.write_bytes(snapshot)
    lines = brk.read_text().splitlines()
    rec = json.loads(lines[min(10, len(lines) - 1)])
    rec["previous_transaction_hash"] = "DEAD" * 16
    lines[min(10, len(lines) - 1)] = json.dumps(rec)
    brk.write_text("\n".join(lines) + "\n")
    bi = eng.verify_closed_loop_ledger_integrity(brk)
    assert bi["status"] == "HASH_CHAIN_BROKEN"
    assert bi["chain_error"]["code"] == "HASH_CHAIN_DISCONTINUITY"


def test_integrity_not_presence_only(ledger_path: Path):
    """A record with required fields but broken chain must NOT report VERIFIED_INTEGRITY."""
    _append("A")
    # Manually append a presence-valid but unchained record (bypass lock helper)
    fake = {
        "transaction_id": "TX-FAKE",
        "previous_transaction_hash": "GENESIS_ROOT",  # wrong — should link to A's hash
        "current_transaction_hash": "1" * 64,
        "timestamp": "2026-07-21T00:00:00Z",
        "graph_manifest_sha256": "g" * 64,
        "evaluation_digest_sha256": "d" * 64,
    }
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fake) + "\n")
    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] != "VERIFIED_INTEGRITY"
    assert integrity["chain_verified"] is False


def _mp_ledger_worker(ledger: str, wid: int, m: int) -> None:
    """Independent process using production append_closed_loop_ledger_entry."""
    import scripts.helm_assurance_engine as hae
    from pathlib import Path

    hae.CLOSED_LOOP_LEDGER_PATH = Path(ledger)
    for j in range(m):
        hae.append_closed_loop_ledger_entry(
            worker_id=f"P{wid}-A{j}",
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


def test_multiprocess_production_append_api(ledger_path: Path):
    """N separate OS processes → same ledger → production append API.

    Thread stress is not final concurrency proof; this is the flock deployment model.
    """
    import multiprocessing

    n, m = 12, 4
    expected = n * m
    procs = [
        multiprocessing.Process(target=_mp_ledger_worker, args=(str(ledger_path), i, m))
        for i in range(n)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0

    lines = [ln for ln in ledger_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == expected
    records = [json.loads(ln) for ln in lines]
    assert len({r["transaction_id"] for r in records}) == expected

    prev = "GENESIS_ROOT"
    for r in records:
        assert r["previous_transaction_hash"] == prev
        prev = r["current_transaction_hash"]

    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "VERIFIED_INTEGRITY"
    assert integrity["chain_verified"] is True
    assert not integrity.get("parse_errors")

    replay = eng.replay_closed_loop_ledger(ledger_path)
    assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
    assert replay["total_chained_transactions"] == expected


def test_extended_burnin_thousands_of_appends(ledger_path: Path):
    """Longer operational evidence: thousands of appends + integrity + replay + fault re-check.

    Methodology unchanged from short burn-in; only scale. Default 2000 for CI time;
    set HELM_LEDGER_BURNIN_N for tens of thousands in overnight runs.
    """
    import os

    n = int(os.environ.get("HELM_LEDGER_BURNIN_N", "2000"))
    for i in range(n):
        _append(f"L{i}")

    integrity = eng.verify_closed_loop_ledger_integrity(ledger_path)
    assert integrity["status"] == "VERIFIED_INTEGRITY"
    assert integrity["total_transactions"] == n
    assert integrity["chain_verified"] is True

    replay = eng.replay_closed_loop_ledger(ledger_path)
    assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
    assert replay["total_chained_transactions"] == n

    # Same tamper checks after long run
    lines = ledger_path.read_text().splitlines()
    rec = json.loads(lines[n // 2])
    rec["current_transaction_hash"] = "a" * 64
    lines[n // 2] = json.dumps(rec)
    torn_path = ledger_path.with_name("post_burnin_tampered.jsonl")
    torn_path.write_text("\n".join(lines) + "\n")
    ti = eng.verify_closed_loop_ledger_integrity(torn_path)
    assert ti["status"] == "HASH_CHAIN_BROKEN"


def test_filesystem_deployment_assumptions_documented():
    """Supported storage assumptions are explicit (local APFS/ext4; NFS fail-closed)."""
    a = eng.FILESYSTEM_DEPLOYMENT_ASSUMPTIONS
    assert a["supported_storage_scope"] == "LOCAL_POSIX_COMPLIANT_FS_ONLY"
    # Accept either key shape (validated_filesystems or supported_filesystems)
    fs = a.get("validated_filesystems") or a.get("supported_filesystems") or []
    assert "apfs" in fs
    assert "ext4" in fs
    unsupported = (
        a.get("unsupported_fail_closed")
        or a.get("unsupported_until_separately_validated")
        or {}
    )
    assert "nfs" in unsupported
    assert "INTER_PROCESS" in a["concurrency_guarantee"]
