"""Operator-hold evaluation with TTL / auto-expiry.

The autonomy daemons read has_live_project_tracker/data/ag_operator_hold.json and
stop executing while `operator_hold_active` is true. A failure-injection test could
set a "simulated" hold and never release it, silently parking the whole fleet.

This module makes holds self-heal: a hold is only *effectively* active if it is
active AND not past its expiry. Simulated/test holds get an implicit TTL so they
cannot latch autonomy indefinitely; genuine manual operator holds never auto-expire
unless an explicit expires_at was set.

Pure and dependency-free so the daemon can import it with a fail-safe fallback.
"""

import datetime

DEFAULT_SIMULATED_TTL_S = 300  # 5 min — a test e-stop must not outlive its test
SIMULATED_OPERATORS = {"failure injector", "failure_injector", "chaos", "test", "injector"}
SIMULATED_CLASSES = {"simulated", "test", "chaos", "injected"}


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def infer_class(hold_data):
    """Return the hold's class. Explicit hold_class wins; otherwise infer from
    operator / reason so legacy simulated holds (no class field) still self-heal."""
    hc = str(hold_data.get("hold_class", "") or "").lower().strip()
    if hc:
        return hc
    op = str(hold_data.get("operator", "") or "").lower().strip()
    reason = str(hold_data.get("reason", "") or "").lower()
    if op in SIMULATED_OPERATORS or "simulat" in reason or "test" in reason:
        return "simulated"
    return "manual"


def evaluate_hold(hold_data, now=None, default_simulated_ttl_s=DEFAULT_SIMULATED_TTL_S):
    """Evaluate whether a hold is *effectively* active.

    Rules:
    - Explicit `expires_at` is always honored.
    - Simulated/test holds without an explicit expires_at get an implicit TTL
      measured from `timestamp` (so a stale test e-stop auto-clears).
    - Manual holds without expires_at never auto-expire (real operator intent).
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    raw_active = bool(hold_data.get("operator_hold_active", False))
    hold_class = infer_class(hold_data)
    expires_at = _parse(hold_data.get("expires_at"))
    ts = _parse(hold_data.get("timestamp"))

    if expires_at is None and hold_class in SIMULATED_CLASSES and ts is not None:
        expires_at = ts + datetime.timedelta(seconds=default_simulated_ttl_s)

    expired = bool(raw_active and expires_at is not None and now >= expires_at)
    effective_active = bool(raw_active and not expired)

    return {
        "effective_active": effective_active,
        "raw_active": raw_active,
        "expired": expired,
        "hold_class": hold_class,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z") if expires_at else None,
        "reason": hold_data.get("reason"),
        "operator": hold_data.get("operator"),
    }


def is_effectively_active(hold_data, now=None):
    return evaluate_hold(hold_data, now=now)["effective_active"]
