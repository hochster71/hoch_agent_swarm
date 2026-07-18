"""Executive-loop instrumentation: metrics accuracy + the degradation detector.

The whole point is to see degradation BEFORE a hard failure, so these tests assert the
detector trips to DEGRADED/AT_RISK on the leading indicators (rising lock-retry rate,
error-cycle rate) rather than only after a crash.
"""
from backend.mission_control.loop_metrics import (
    LoopMetrics, LOCK_RETRY_CRIT, ERROR_RATE_CRIT,
)


def _fresh():
    return LoopMetrics()


def test_cycle_counts_and_throughput():
    m = _fresh()
    m.record_cycle(state="IDLE")
    m.record_cycle(state="ACTIVE", dispatched=3, passed=2, failed=1, seconds=4.0)
    m.record_cycle(state="ERROR")
    snap = m.snapshot()
    assert snap["cycles"] == {"total": 3, "idle": 1, "active": 1, "error": 1}
    assert snap["missions"]["dispatched"] == 3
    assert snap["missions"]["passed"] == 2
    assert snap["missions"]["failed"] == 1
    assert snap["missions"]["throughput_per_min"] >= 0.0


def test_lock_contention_recorded():
    m = _fresh()
    m.record_lock_retry("persist_status:T1", 0.4)
    m.record_lock_retry("persist_status:T1", 0.8)
    snap = m.snapshot()
    assert snap["lock_contention"]["retries_total"] == 2
    assert abs(snap["lock_contention"]["wait_seconds_total"] - 1.2) < 1e-6
    assert snap["lock_contention"]["by_op"]["persist_status:T1"] == 2


def test_healthy_when_nominal():
    m = _fresh()
    for _ in range(10):
        m.record_cycle(state="IDLE", seconds=1.0)
    assert m.assess()["state"] == "HEALTHY"


def test_degrades_on_rising_lock_retries():
    """Sustained lock-retries per cycle above the critical rate -> AT_RISK, BEFORE a crash."""
    m = _fresh()
    for _ in range(10):
        for _ in range(int(LOCK_RETRY_CRIT) + 1):
            m.record_lock_retry("persist_status:X", 0.5)
        m.record_cycle(state="ACTIVE", seconds=1.0)
    a = m.assess()
    assert a["state"] == "AT_RISK", a
    assert any("lock-retry" in r for r in a["reasons"])


def test_degrades_on_error_cycles():
    """A high fraction of ERROR cycles -> AT_RISK (the state cycle 506 would have shown)."""
    m = _fresh()
    for i in range(10):
        m.record_cycle(state="ERROR" if i < int(ERROR_RATE_CRIT * 10) + 1 else "IDLE", seconds=1.0)
    a = m.assess()
    assert a["state"] in ("DEGRADED", "AT_RISK")
    assert any("error-cycle" in r for r in a["reasons"])


def test_latency_spike_flags_degraded():
    m = _fresh()
    for _ in range(8):
        m.record_cycle(state="IDLE", seconds=1.0)
    m.record_cycle(state="IDLE", seconds=10.0)  # 10x median
    a = m.assess()
    assert a["state"] == "DEGRADED"
    assert any("latency" in r for r in a["reasons"])
