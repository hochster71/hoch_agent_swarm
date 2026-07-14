"""AU-9 — Protection of Audit Information. The test comes BEFORE the fix.

This is the control that makes a baseline STICK.

Demonstrated on 2026-07-14 against the live system: a record was deleted from the middle of
coordination/council/daemon/task_lease_ledger.jsonl (1269 -> 1268 records) and NOTHING detected
it. No chain, no signature, no integrity check. The deletion was undetectable.

That is why no baseline has ever held. A baseline is only as durable as the evidence plane beneath
it, and this one is append-only by CONVENTION, not by ENFORCEMENT.

These tests fail until the evidence plane is tamper-evident. They are the definition of done.
"""
from __future__ import annotations

import json
import pytest

from backend.truth.evidence_chain import (        # does not exist yet — that is the point
    append_record,
    verify_chain,
    ChainBroken,
)


def _read(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------- chain integrity
def test_each_record_binds_to_its_predecessor(tmp_path):
    led = tmp_path / "ledger.jsonl"
    for i in range(5):
        append_record(led, {"task_id": f"T{i}", "status": "COMPLETE"})
    rows = _read(led)
    assert rows[0]["prev_hash"] == "GENESIS"
    for a, b in zip(rows, rows[1:]):
        assert b["prev_hash"] == a["entry_hash"], "record does not bind to its predecessor"


def test_clean_chain_verifies(tmp_path):
    led = tmp_path / "ledger.jsonl"
    for i in range(20):
        append_record(led, {"task_id": f"T{i}"})
    assert verify_chain(led) is True


# ---------------------------------------------------------------- tamper detection
def test_DELETING_a_record_from_the_middle_is_detected(tmp_path):
    """THE EXACT ATTACK RUN AGAINST THE LIVE SYSTEM. It succeeded silently. It must not."""
    led = tmp_path / "ledger.jsonl"
    for i in range(20):
        append_record(led, {"task_id": f"T{i}"})
    lines = led.read_text().splitlines()
    del lines[10]                                   # silently remove history
    led.write_text("\n".join(lines) + "\n")
    with pytest.raises(ChainBroken):
        verify_chain(led)


def test_EDITING_a_record_in_place_is_detected(tmp_path):
    led = tmp_path / "ledger.jsonl"
    for i in range(10):
        append_record(led, {"task_id": f"T{i}", "status": "FAILED"})
    rows = _read(led)
    rows[4]["status"] = "COMPLETE"                  # rewrite a failure into a success
    led.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    with pytest.raises(ChainBroken):
        verify_chain(led)


def test_REORDERING_records_is_detected(tmp_path):
    led = tmp_path / "ledger.jsonl"
    for i in range(10):
        append_record(led, {"task_id": f"T{i}"})
    rows = _read(led)
    rows[3], rows[7] = rows[7], rows[3]
    led.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    with pytest.raises(ChainBroken):
        verify_chain(led)


def test_TRUNCATING_the_tail_is_detected(tmp_path):
    """Cutting off the end must not silently look like 'less work happened'."""
    led = tmp_path / "ledger.jsonl"
    for i in range(10):
        append_record(led, {"task_id": f"T{i}"})
    head_hash = _read(led)[-1]["entry_hash"]
    lines = led.read_text().splitlines()[:6]
    led.write_text("\n".join(lines) + "\n")
    with pytest.raises(ChainBroken):
        verify_chain(led, expected_head=head_hash)


def test_APPENDING_a_forged_record_is_detected(tmp_path):
    led = tmp_path / "ledger.jsonl"
    for i in range(5):
        append_record(led, {"task_id": f"T{i}"})
    with led.open("a") as f:
        f.write(json.dumps({"task_id": "FORGED", "status": "COMPLETE",
                            "prev_hash": "made-up", "entry_hash": "also-made-up"}) + "\n")
    with pytest.raises(ChainBroken):
        verify_chain(led)


# ---------------------------------------------------------------- fail closed
def test_a_broken_chain_reads_as_CONTRADICTED_not_as_data(tmp_path):
    """A broken chain must NEVER be silently treated as valid history.
    Missing evidence is UNKNOWN. TAMPERED evidence is CONTRADICTED. Neither is PASS."""
    led = tmp_path / "ledger.jsonl"
    for i in range(5):
        append_record(led, {"task_id": f"T{i}"})
    lines = led.read_text().splitlines()
    del lines[2]
    led.write_text("\n".join(lines) + "\n")
    try:
        verify_chain(led)
        pytest.fail("verify_chain returned instead of raising on a broken chain")
    except ChainBroken as e:
        assert "CONTRADICTED" in str(e).upper() or "BROKEN" in str(e).upper()


def test_sealer_cannot_emit_PASS_over_a_broken_chain(tmp_path):
    """The whole point. A PASS issued over rewritten history is worse than no PASS at all."""
    from scripts.council.seal_soak_phase import chain_precondition   # does not exist yet
    led = tmp_path / "ledger.jsonl"
    for i in range(5):
        append_record(led, {"task_id": f"T{i}"})
    lines = led.read_text().splitlines()
    del lines[2]
    led.write_text("\n".join(lines) + "\n")
    ok, reason = chain_precondition(led)
    assert ok is False
    assert "chain" in reason.lower()


# ---------------------------------------------------------------- concurrency (added after a real
# 4-worker soak broke its own chain: append_record was read-head-then-append with no lock)
def test_concurrent_writers_do_not_break_the_chain(tmp_path):
    """N threads hammering append_record in parallel must still produce ONE linear chain.
    The soak runs 4 concurrent workers; without a lock, two of them read the same prev_hash and
    the chain broke at the first concurrent pair. flock must serialize the critical section."""
    import threading
    led = tmp_path / "ledger.jsonl"
    errors = []
    def worker(k):
        try:
            for i in range(25):
                append_record(led, {"task": f"T{k}-{i}"})
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors, f"append raised under concurrency: {errors[:2]}"
    # 8 threads x 25 = 200 rows, and the chain MUST verify end to end
    rows = [l for l in led.read_text().splitlines() if l.strip()]
    assert len(rows) == 200, f"lost writes under concurrency: {len(rows)}/200"
    assert verify_chain(led) is True
