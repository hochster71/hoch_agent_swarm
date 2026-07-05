import datetime

from backend.runtime_truth.operator_hold import evaluate_hold, is_effectively_active

UTC = datetime.timezone.utc


def _t(s):
    return s.isoformat().replace("+00:00", "Z")


def test_manual_hold_never_auto_expires():
    now = datetime.datetime(2026, 7, 5, 18, 0, tzinfo=UTC)
    old = now - datetime.timedelta(days=3)
    h = {"operator_hold_active": True, "operator": "Michael Hoch",
         "reason": "Manual operator intervention", "timestamp": _t(old)}
    assert is_effectively_active(h, now=now) is True  # real e-stop stays on


def test_simulated_hold_auto_expires():
    now = datetime.datetime(2026, 7, 5, 18, 0, tzinfo=UTC)
    old = now - datetime.timedelta(hours=1)  # well past 300s TTL
    h = {"operator_hold_active": True, "operator": "Failure Injector",
         "reason": "Simulated emergency stop", "timestamp": _t(old)}
    res = evaluate_hold(h, now=now)
    assert res["raw_active"] is True
    assert res["expired"] is True
    assert res["effective_active"] is False  # THE bug that latched the fleet: now self-heals


def test_simulated_hold_still_active_within_ttl():
    now = datetime.datetime(2026, 7, 5, 18, 0, tzinfo=UTC)
    recent = now - datetime.timedelta(seconds=60)  # inside 300s TTL
    h = {"operator_hold_active": True, "operator": "Failure Injector",
         "reason": "Simulated emergency stop", "timestamp": _t(recent)}
    assert is_effectively_active(h, now=now) is True  # test window still valid


def test_explicit_expires_at_is_honored():
    now = datetime.datetime(2026, 7, 5, 18, 0, tzinfo=UTC)
    h = {"operator_hold_active": True, "operator": "Michael Hoch", "hold_class": "manual",
         "reason": "scheduled maintenance window",
         "timestamp": _t(now - datetime.timedelta(hours=2)),
         "expires_at": _t(now - datetime.timedelta(minutes=1))}
    assert is_effectively_active(h, now=now) is False  # explicit expiry passed


def test_inactive_hold_is_inactive():
    h = {"operator_hold_active": False}
    assert is_effectively_active(h) is False


def test_class_inference():
    from backend.runtime_truth.operator_hold import infer_class
    assert infer_class({"operator": "Failure Injector"}) == "simulated"
    assert infer_class({"reason": "Simulated emergency stop"}) == "simulated"
    assert infer_class({"operator": "Michael Hoch", "reason": "manual"}) == "manual"
    assert infer_class({"hold_class": "SIMULATED"}) == "simulated"
