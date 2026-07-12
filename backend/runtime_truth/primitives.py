"""RUNTIME TRUTH PRIMITIVES — REQ-GOV-005.

RATIFIED RULE
-------------
Missing, unreadable, stale, malformed, or unavailable source state must be represented
as an EXPLICIT truth state. It must NEVER be substituted with success, completion,
readiness, freshness, zero age, current time, empty blocker lists, default percentages,
or synthetic timestamps.

WHAT THIS REPLACES
------------------
backend/pert_server.py::wrap_telemetry_dict manufactured truth two ways:

  1. `if not last_updated_iso: last_updated_iso = datetime.now(timezone.utc)`
     A field with NO timestamp reported freshness = 0.0s and confidence = HIGH.
     Absence of evidence rendered as the freshest possible evidence.

  2. Callers passed a fallback default -- e.g.
     `compute_gap.get("goal_completion_percent", 90.0)` -- so a MISSING source produced
     value=90.0, source=autonomous_cadence_telemetry, freshness=0.0s, confidence=HIGH.
     A number nobody measured, attributed to a system that never ran.

Neither is possible here. No code path in this module invents a value or a time.

TIMESTAMP KINDS (ratified distinction)
--------------------------------------
  generated_at      permitted: THIS artifact is genuinely being generated right now.
  observed_at       must come from the observation. Never now().
  source_updated_at must come from the source. Never now().
  validated_at      set ONLY when the validator actually executed.
  age_seconds       null when no valid timestamp exists. Never 0.
"""
from __future__ import annotations

import datetime
from typing import Any

# --- explicit truth states -------------------------------------------------
UNKNOWN = "UNKNOWN"
MISSING = "MISSING"
STALE = "STALE"
ERROR = "ERROR"
UNVERIFIED = "UNVERIFIED"
OK = "OK"

TRUTH_STATES = {UNKNOWN, MISSING, STALE, ERROR, UNVERIFIED, OK}

# Confidence may never default to HIGH. Absence of evidence is never high confidence.
CONF_NONE = "NONE"
CONF_LOW = "LOW"
CONF_HIGH = "HIGH"

_SENTINEL = object()


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def generated_at() -> str:
    """The ONLY legitimate use of now(): stamping the artifact being generated now."""
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_ts(value: Any) -> datetime.datetime | None:
    """Parse a timestamp. Returns None -- never now() -- when it cannot."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.datetime.fromisoformat(value.strip().rstrip("Z"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def freshness(source_timestamp: Any, sla_seconds: float | None = None) -> dict:
    """Freshness of a SOURCE observation.

    A missing or unparseable timestamp yields the ratified shape:
        {"freshness": "UNKNOWN", "fresh": False, "age_seconds": None,
         "timestamp_status": "MISSING"}
    It never yields age 0, and never yields fresh=True.
    """
    dt = parse_ts(source_timestamp)
    if dt is None:
        return {
            "freshness": UNKNOWN,
            "fresh": False,
            "age_seconds": None,
            "timestamp_status": MISSING if source_timestamp in (None, "") else ERROR,
            "source_updated_at": None,
        }

    age = round((utc_now() - dt).total_seconds(), 2)
    if age < 0:
        # A source timestamp in the future is not "fresh" -- it is broken.
        return {
            "freshness": UNKNOWN,
            "fresh": False,
            "age_seconds": None,
            "timestamp_status": ERROR,
            "source_updated_at": dt.isoformat().replace("+00:00", "Z"),
        }

    stale = sla_seconds is not None and age > float(sla_seconds)
    return {
        "freshness": STALE if stale else OK,
        "fresh": not stale,
        "age_seconds": age,
        "timestamp_status": OK,
        "source_updated_at": dt.isoformat().replace("+00:00", "Z"),
    }


def truth(
    value: Any = _SENTINEL,
    *,
    source: str,
    source_updated_at: Any = None,
    sla_seconds: float | None = None,
    verified: bool = False,
) -> dict:
    """Wrap an observed value in explicit truth. The ONLY permitted telemetry wrapper.

    There is NO `fallback` parameter, by design. A caller with nothing to report passes
    nothing and gets MISSING. It is impossible to express "use 90.0 if absent".
    """
    missing = value is _SENTINEL or value is None
    f = freshness(source_updated_at, sla_seconds)

    if missing:
        state, confidence, out_value = MISSING, CONF_NONE, None
    elif f["timestamp_status"] in (MISSING, ERROR):
        # We have a number but cannot say WHEN it was true. That is not knowledge.
        state, confidence, out_value = UNVERIFIED, CONF_LOW, value
    elif f["freshness"] == STALE:
        state, confidence, out_value = STALE, CONF_LOW, value
    elif not verified:
        state, confidence, out_value = UNVERIFIED, CONF_LOW, value
    else:
        state, confidence, out_value = OK, CONF_HIGH, value

    return {
        "value": out_value,
        "state": state,
        "source": source,
        "confidence": confidence,
        "generated_at": generated_at(),      # this artifact, right now: legitimate
        "source_updated_at": f["source_updated_at"],
        "observed_at": f["source_updated_at"],
        "validated_at": generated_at() if (verified and state == OK) else None,
        "freshness": f["freshness"],
        "fresh": f["fresh"],
        "age_seconds": f["age_seconds"],
        "timestamp_status": f["timestamp_status"],
    }


def unknown(source: str, reason: str = "SOURCE_UNAVAILABLE") -> dict:
    """Explicit UNKNOWN. Use this instead of ANY default value."""
    t = truth(source=source)
    t["state"] = UNKNOWN
    t["reason"] = reason
    return t


def error(source: str, reason: str) -> dict:
    t = truth(source=source)
    t["state"] = ERROR
    t["timestamp_status"] = ERROR
    t["reason"] = reason
    return t


def is_displayable_success(t: dict) -> bool:
    """A consumer may treat a value as good ONLY when it is OK. Never on UNKNOWN."""
    return isinstance(t, dict) and t.get("state") == OK and t.get("value") is not None
