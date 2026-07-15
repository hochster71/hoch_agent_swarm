"""AU-9 continuity regression — concurrent appends must NOT fork the hash chain.

Root cause of the 11 historical link discontinuities in spend_ledger.jsonl:
`_append` did read-last-hash then append WITHOUT a cross-process lock, so two
writers computed the same prev_hash and both appended -> the chain forked.

The fix serializes the read+append critical section under an exclusive flock.
This test spawns real concurrent PROCESSES hammering one ledger and asserts the
resulting chain has zero link breaks and zero hash mismatches.
"""
import json
import multiprocessing as mp
import hashlib
from pathlib import Path

from backend.mission_control.spend_meter import SpendMeter


def _hammer(path_str: str, n: int, worker: int) -> None:
    sm = SpendMeter(path=Path(path_str))
    for i in range(n):
        sm._append({
            "ts": f"w{worker}-{i}",
            "adapter": "test", "task_id": f"t{worker}-{i}",
            "cost_usd": 0.0, "cost_state": "TEST",
        })


def _verify(path: Path):
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    prev, link_breaks, hash_breaks = "GENESIS", 0, 0
    for i, e in enumerate(rows):
        if e.get("prev_hash") != prev:
            link_breaks += 1
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != e.get("entry_hash"):
            hash_breaks += 1
        prev = e.get("entry_hash", "")
    return len(rows), link_breaks, hash_breaks


def test_concurrent_appends_keep_chain_intact(tmp_path):
    ledger = tmp_path / "spend_ledger.jsonl"
    workers, per = 8, 30
    procs = [mp.Process(target=_hammer, args=(str(ledger), per, w)) for w in range(workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0, "a writer process failed"

    total, link_breaks, hash_breaks = _verify(ledger)
    assert total == workers * per, f"expected {workers*per} rows, got {total} (lost writes)"
    assert link_breaks == 0, f"chain forked under concurrency: {link_breaks} link breaks"
    assert hash_breaks == 0, f"hash mismatch: {hash_breaks}"


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "spend_ledger.jsonl"
        procs = [mp.Process(target=_hammer, args=(str(p), 30, w)) for w in range(8)]
        [x.start() for x in procs]
        [x.join() for x in procs]
        print(_verify(p))
