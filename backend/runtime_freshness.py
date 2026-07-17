"""HELM runtime-freshness service — "always current or honestly stale".

DOCTRINE
--------
Every HELM truth source has a natural refresh cadence. The legacy live API stamps
*everything* with a single blanket rule (``fresh = "FRESH" if age < 86400 else
"STALE"``) — a 24h window so wide that a factory registry could rot for 73 hours and
still badge FRESH. That is a decoration, not a dashboard.

This module gives each signal a TIGHT, per-signal budget and yields one of three
honest states:

    FRESH    — observed within its own budget
    STALE    — a real, parseable timestamp but older than its budget
    UNKNOWN  — the source is missing / empty / unparseable / has no usable timestamp

There are NO fallbacks that invent liveness. If we cannot prove an age, the answer is
UNKNOWN — never FRESH. Overall state is the WORST of all signals (UNKNOWN worst, then
STALE, then FRESH), because a wall is only as trustworthy as its least-trustworthy tile.

Pure stdlib. READ-ONLY: this module never writes, moves, or mutates any state file.
It can run standalone right now with no server:  ``python3 -m backend.runtime_freshness``
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

# State ordering — higher rank == worse == wins the "overall" reduction.
_RANK = {"FRESH": 0, "STALE": 1, "UNKNOWN": 2}


# ---------------------------------------------------------------------------
# FRESHNESS_BUDGETS — the whole point. Each signal gets a realistic budget tied
# to how often its producer actually rewrites it. Justifications inline.
# ---------------------------------------------------------------------------
#
# A signal is FRESH only while age <= budget_seconds. These replace the blanket
# 86400s window in helm_live_api.py (~line 192) that let stale tiles look alive.
FRESHNESS_BUDGETS: Dict[str, int] = {
    # Sidecar self-rebuilds on a ~30s TTL and the file itself declares
    # max_age_seconds=60. 120s = 2x its own contract, tight enough to catch a
    # dead sidecar within ~2 min.
    "control_plane": 120,
    # Supervisor heartbeat should tick continuously; 300s (5 min) flags a
    # supervisor that has gone quiet without being noisy about a single skipped beat.
    "supervisor_heartbeat": 300,
    # Orchestration authority file carries its OWN max_age of 600s; we mirror it
    # so our badge agrees with the runtime's own staleness contract.
    "orchestration_authority": 600,
    # Runtime state is polled on the supervisor loop; 600s (10 min) matches the
    # authority cadence and catches a frozen runtime loop.
    "helm_runtime_state": 600,
    # Factory registry changes far less often than heartbeats, but 24h is absurd
    # (it silently went 73h stale). 1800s (30 min) is generous for a registry yet
    # still surfaces a factory rebuild pipeline that has stopped stamping it.
    "helm_agent_registry": 1800,
    # Goal state is recomputed roughly hourly; 3600s (1h) is the natural budget.
    "goal_state": 3600,
    # Mission state shares the goal recompute cadence; 3600s (1h).
    "mission_state": 3600,
    # Live soak writes runtime-truth snapshots frequently; 300s (5 min) proves the
    # soak is actually advancing rather than showing a frozen last line.
    "runtime_truth_snapshot": 300,
}


# ---------------------------------------------------------------------------
# SIGNAL_SPECS — how to locate each source and where its timestamp lives.
#
# kind:
#   "json"       -> parse whole-file JSON, read first present field in ts_fields
#   "jsonl_last" -> parse LAST non-empty line as JSON, read first present ts_field
# ts_fields: candidate timestamp keys, tried in order. Empty list => use file mtime.
# Any resolver falls back to file mtime when no ts_field yields a value, so a file
# that exists but carries no timestamp is still aged honestly (never invented).
# ---------------------------------------------------------------------------
SIGNAL_SPECS: Dict[str, Dict[str, Any]] = {
    "control_plane": {
        "path": "has_live_project_tracker/data/control_plane_status.json",
        "kind": "json",
        "ts_fields": ["as_of", "observed_at", "timestamp"],
    },
    "supervisor_heartbeat": {
        "path": "has_live_project_tracker/data/helm_supervisor_heartbeat.json",
        "kind": "json",
        "ts_fields": ["timestamp", "observed_at"],
    },
    "orchestration_authority": {
        "path": "has_live_project_tracker/data/orchestration_bridge_control.json",
        "kind": "json",
        # No whole-file timestamp field -> aged by file mtime (its real last write).
        "ts_fields": [],
    },
    "helm_runtime_state": {
        "path": "has_live_project_tracker/data/helm_runtime_state.json",
        "kind": "json",
        "ts_fields": ["last_checked", "observed_at", "last_run"],
    },
    "helm_agent_registry": {
        "path": "has_live_project_tracker/data/helm_agent_registry.json",
        "kind": "json",
        "ts_fields": ["observed_at", "as_of", "updated_at", "generated_at"],
    },
    "goal_state": {
        "path": "coordination/goal/goal_state.json",
        "kind": "json",
        "ts_fields": ["computed_at", "observed_at", "as_of"],
    },
    "mission_state": {
        "path": "coordination/goal/mission_state.json",
        "kind": "json",
        "ts_fields": ["computed_at", "observed_at", "as_of"],
    },
    "runtime_truth_snapshot": {
        # Resolved dynamically at eval time to the newest soak package's snapshot.
        "path": None,
        "kind": "jsonl_last",
        "ts_fields": ["at", "observed_at", "timestamp"],
        "resolver": "newest_soak_snapshot",
    },
}


# ---------------------------------------------------------------------------
# Helpers (pure, read-only)
# ---------------------------------------------------------------------------
def _now(now: Optional[datetime] = None) -> datetime:
    return now or datetime.now(timezone.utc)


def parse_ts(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp (Z or offset, fractional seconds ok) to aware UTC.

    Returns None if unparseable. Never raises."""
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # Try trimming to seconds precision as a last resort.
        try:
            dt = datetime.fromisoformat(s[:19])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def newest_soak_snapshot(root: Path) -> Optional[Path]:
    """Newest HELM-SOAK-24H-* package's runtime_truth_snapshots.jsonl, or None."""
    pkgs_dir = root / "coordination" / "council" / "live_proof_packages"
    if not pkgs_dir.exists():
        return None
    candidates = sorted(pkgs_dir.glob("HELM-SOAK-24H-*"), key=lambda p: p.name, reverse=True)
    for pkg in candidates:
        snap = pkg / "runtime_truth_snapshots.jsonl"
        if snap.exists():
            return snap
    return None


def _resolve_path(name: str, spec: Dict[str, Any], root: Path) -> Optional[Path]:
    resolver = spec.get("resolver")
    if resolver == "newest_soak_snapshot":
        return newest_soak_snapshot(root)
    p = spec.get("path")
    if p is None:
        return None
    return root / p


def _observed_at(path: Path, spec: Dict[str, Any]) -> Optional[datetime]:
    """Best observed_at for a source: first present ts_field, else file mtime.

    Returns None only if the file cannot be read/parsed at all AND has no mtime."""
    kind = spec.get("kind", "json")
    ts_fields = spec.get("ts_fields", []) or []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    doc: Any = None
    try:
        if kind == "jsonl_last":
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if lines:
                doc = json.loads(lines[-1])
        else:
            doc = json.loads(text) if text.strip() else None
    except (ValueError, json.JSONDecodeError):
        doc = None  # unparseable -> fall through to mtime

    if isinstance(doc, dict):
        for field in ts_fields:
            dt = parse_ts(doc.get(field))
            if dt is not None:
                return dt

    # Fall back to real file mtime (tz-independent epoch).
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate_signal(
    name: str,
    spec: Optional[Dict[str, Any]] = None,
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Evaluate one signal -> dict with state FRESH|STALE|UNKNOWN and its evidence."""
    root = root or ROOT
    spec = spec or SIGNAL_SPECS.get(name, {})
    budget = int(FRESHNESS_BUDGETS.get(name, 0)) or int(spec.get("budget", 0))
    now_dt = _now(now)

    path = _resolve_path(name, spec, root)
    rel = None
    if path is not None:
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)

    base = {
        "name": name,
        "source_path": rel,
        "observed_at": None,
        "age_seconds": None,
        "budget_seconds": budget,
    }

    if path is None:
        return {**base, "state": "UNKNOWN", "reason": "no source could be resolved"}
    if not path.exists():
        return {**base, "state": "UNKNOWN", "reason": f"source file missing: {rel}"}

    observed = _observed_at(path, spec)
    if observed is None:
        return {**base, "state": "UNKNOWN",
                "reason": "source unreadable or has no usable timestamp"}

    age = (now_dt - observed).total_seconds()
    if age < 0:
        age = 0.0  # clock skew / future stamp -> treat as just-observed, not stale
    observed_iso = observed.isoformat().replace("+00:00", "Z")

    if budget <= 0:
        return {**base, "observed_at": observed_iso, "age_seconds": round(age, 1),
                "state": "UNKNOWN", "reason": "no budget configured for signal"}

    if age <= budget:
        state, reason = "FRESH", f"age {age:.0f}s within budget {budget}s"
    else:
        state, reason = "STALE", f"age {age:.0f}s exceeds budget {budget}s"

    return {**base, "observed_at": observed_iso, "age_seconds": round(age, 1),
            "state": state, "reason": reason}


def evaluate_all(
    specs: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Evaluate every signal. Overall state = worst of all signals."""
    specs = specs if specs is not None else SIGNAL_SPECS
    root = root or ROOT
    now_dt = _now(now)
    signals: List[Dict[str, Any]] = [
        evaluate_signal(name, spec, root=root, now=now_dt) for name, spec in specs.items()
    ]
    overall = "FRESH"
    for s in signals:
        if _RANK[s["state"]] > _RANK[overall]:
            overall = s["state"]
    counts = {"FRESH": 0, "STALE": 0, "UNKNOWN": 0}
    for s in signals:
        counts[s["state"]] += 1
    return {
        "service": "helm.runtime_freshness",
        "evaluated_at": now_dt.isoformat().replace("+00:00", "Z"),
        "overall_state": overall,
        "counts": counts,
        "signals": signals,
    }


def render_board(result: Optional[Dict[str, Any]] = None) -> str:
    """Compact human-readable freshness board."""
    result = result or evaluate_all()
    icon = {"FRESH": "[FRESH]  ", "STALE": "[STALE]  ", "UNKNOWN": "[UNKNOWN]"}
    lines = [
        "HELM RUNTIME FRESHNESS BOARD",
        f"evaluated_at: {result['evaluated_at']}",
        f"OVERALL: {result['overall_state']}   "
        f"(FRESH={result['counts']['FRESH']} "
        f"STALE={result['counts']['STALE']} "
        f"UNKNOWN={result['counts']['UNKNOWN']})",
        "-" * 78,
    ]
    for s in result["signals"]:
        age = "n/a" if s["age_seconds"] is None else f"{s['age_seconds']:.0f}s"
        lines.append(
            f"{icon.get(s['state'], s['state']):9} {s['name']:24} "
            f"age={age:>9} / budget={s['budget_seconds']}s  :: {s['reason']}"
        )
    lines.append("-" * 78)
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_board())
