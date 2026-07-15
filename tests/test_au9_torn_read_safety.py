"""AU-9 verify must be torn-read-safe AND still catch real tampering.

Background: an earlier investigation reported '11 spend-ledger link breaks'. Git later
proved that was FALSE — 0 rows ever changed, the committed chain had 0 breaks. The
'breaks' were a torn read: the verifier read the file with a plain read while the live
council was appending concurrently. verify_chain now reads under a SHARED flock, so an
in-flight append (holding the EXCLUSIVE flock) can never yield a torn read.

These tests prove:
  1. A reader calling verify_chain repeatedly WHILE a writer hammers the ledger never
     sees a false break — every read is internally consistent. (the real fix)
  2. Genuine tampering (an edited row) is still detected. (detection not weakened)
"""
import json
import hashlib
import multiprocessing as mp
import time
from pathlib import Path

from backend.mission_control.spend_meter import SpendMeter


def _writer(path_str: str, n: int):
    sm = SpendMeter(path=Path(path_str))
    for i in range(n):
        sm._append({"ts": f"w-{i}", "adapter": "x", "cost_usd": 0.0, "cost_state": "TEST"})
        time.sleep(0.001)


def test_verify_chain_is_torn_read_safe_under_concurrent_writes(tmp_path):
    ledger = tmp_path / "spend_ledger.jsonl"
    SpendMeter(path=ledger)._append({"ts": "seed", "adapter": "x", "cost_usd": 0.0, "cost_state": "TEST"})

    w = mp.Process(target=_writer, args=(str(ledger), 120))
    w.start()
    reader = SpendMeter(path=ledger)
    false_breaks = 0
    reads = 0
    while w.is_alive():
        ok, bad = reader.verify_chain()
        reads += 1
        if not ok:                      # writes are clean, so any 'break' is a torn read
            false_breaks += 1
    w.join(timeout=30)
    assert reads > 5, f"expected many concurrent reads, got {reads}"
    assert false_breaks == 0, f"{false_breaks}/{reads} reads saw a FALSE break (torn read not fixed)"


def test_real_tampering_is_still_detected(tmp_path):
    ledger = tmp_path / "spend_ledger.jsonl"
    sm = SpendMeter(path=ledger)
    for i in range(4):
        sm._append({"ts": f"t{i}", "adapter": "x", "cost_usd": 0.0, "cost_state": "TEST"})
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    rows[2]["cost_usd"] = 999.99      # edit a row WITHOUT recomputing its entry_hash
    ledger.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")

    ok, bad = SpendMeter(path=ledger).verify_chain()
    assert not ok
    assert any("entry_hash mismatch" in b for b in bad), bad
