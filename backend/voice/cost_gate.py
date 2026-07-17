"""HELM Voice cost gate — fail-closed dollar enforcement for paid TTS.

Phase 2 of the voice sidecar (design: docs/evidence/runtime/voice-sidecar-phase-2-design.md).

Turns `daily_budget_usd` (config/voice_policy.yaml) from a *displayed* number into an
*enforced* ceiling. Provides:
  - a deterministic pre-flight per-call cost ESTIMATE (chars x provider unit price),
  - three FAIL-CLOSED ceilings (per_call / daily / monthly) read from policy,
  - an append-only usage ledger writer (data/runtime/voice_usage_ledger.jsonl) + daily rollup,
  - a DOORSTEP-shaped staged verdict on budget exhaustion (stage at the founder door; never
    auto-spend, never auto-raise a ceiling).

Doctrine (HELM): no_fake_green / fail-closed.
  * Provider price UNKNOWN            => BLOCK (no spend on a made-up rate).
  * Cost master switch off            => BLOCK (default posture).
  * Any ceiling would be crossed      => BLOCK + fall back to always-free local_tts.
  * Ledger unreadable OR unwritable   => BLOCK (money is tracked or not spent).
The chain always terminates at local_tts, which is never gated.

This module has NO paid side effects and makes NO network calls. It only estimates,
reads/writes a local JSONL ledger, and returns a verdict.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.voice.policy import load_voice_policy

ROOT = Path(__file__).resolve().parents[2]

USAGE_SCHEMA = "helm-voice-usage-v1"
STAGE_SCHEMA = "helm-voice-stage-v1"

# gate_result values recorded in the ledger
ALLOWED = "ALLOWED"
BLOCKED_BUDGET = "BLOCKED_BUDGET"
BLOCKED_FAILCLOSED = "BLOCKED_FAILCLOSED"
FALLBACK_LOCAL = "FALLBACK_LOCAL"

# Providers whose spend HELM must meter. local_tts is free and NEVER gated;
# grok_builtin is billed externally by xAI (UNKNOWN to HELM) so it is not HELM-metered.
FREE_PROVIDERS = {"local_tts"}
EXTERNAL_PROVIDERS = {"grok_builtin"}


class LedgerError(RuntimeError):
    """Raised when the usage ledger exists but cannot be read/parsed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_day(ts: Optional[str] = None) -> str:
    if ts:
        return str(ts)[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_month(ts: Optional[str] = None) -> str:
    if ts:
        return str(ts)[:7]
    return datetime.now(timezone.utc).strftime("%Y-%m")


# --------------------------------------------------------------------------- config

def cost_config(policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Read the fail-closed cost knobs from policy (falls back to hard defaults)."""
    p = policy if policy is not None else load_voice_policy()

    def _num(key: str, default: float) -> float:
        try:
            v = p.get(key, default)
            return float(v) if v is not None else float(default)
        except (TypeError, ValueError):
            return float(default)

    return {
        "cost_enabled": bool(p.get("cost_enabled", False)),
        "per_call_ceiling_usd": _num("per_call_ceiling_usd", 0.0),
        "daily_budget_usd": _num("daily_budget_usd", 0.0),
        "monthly_budget_usd": _num("monthly_budget_usd", 0.0),
        "doorstep_on_budget_exhaustion": bool(p.get("doorstep_on_budget_exhaustion", True)),
    }


def _provider_rate(provider: str, policy: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """USD per 1000 chars for a provider, or None (UNKNOWN => fail-closed)."""
    p = policy if policy is not None else load_voice_policy()
    key = f"{provider}_usd_per_1k_chars"
    raw = p.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def default_ledger_path(policy: Optional[Dict[str, Any]] = None) -> Path:
    p = policy if policy is not None else load_voice_policy()
    rel = str(p.get("voice_usage_ledger") or "data/runtime/voice_usage_ledger.jsonl")
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------- estimate

def estimate_cost_usd(
    billable_chars: int,
    provider: str = "elevenlabs",
    policy: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[float], bool, Optional[float]]:
    """Deterministic pre-flight estimate.

    Returns (estimated_cost_usd, price_unknown, rate_usd_per_1k).
    Free providers estimate 0.0 (known). Unknown-priced providers => (None, True, None).
    """
    chars = max(0, int(billable_chars or 0))
    if provider in FREE_PROVIDERS:
        return 0.0, False, 0.0
    rate = _provider_rate(provider, policy)
    if rate is None:
        return None, True, None
    est = round((chars / 1000.0) * rate, 6)
    return est, False, rate


# --------------------------------------------------------------------------- ledger

def append_usage(record: Dict[str, Any], ledger_path: Optional[Path] = None) -> bool:
    """Append one usage record (append-only, crash-safe-ish). Returns True on success.

    A False return is load-bearing: callers MUST fail-closed (no untracked spend) on it (F8).
    """
    try:
        path = Path(ledger_path) if ledger_path else default_ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def _read_records(ledger_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read all usage records. Missing file => []. Unreadable/corrupt => LedgerError."""
    path = Path(ledger_path) if ledger_path else default_ledger_path()
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    except Exception as e:  # pragma: no cover - defensive
        raise LedgerError(f"usage ledger unreadable: {e}") from e
    return out


def _record_spend(rec: Dict[str, Any]) -> float:
    """Spend attributed to a served record: actual if provider-reported, else estimate."""
    if str(rec.get("gate_result")) != ALLOWED:
        return 0.0
    actual = rec.get("actual_cost_usd")
    if isinstance(actual, (int, float)):
        return float(actual)
    est = rec.get("estimated_cost_usd")
    return float(est) if isinstance(est, (int, float)) else 0.0


def daily_rollup(
    ledger_path: Optional[Path] = None,
    day: Optional[str] = None,
) -> Dict[str, Any]:
    """Derived (regenerable) rollup for a UTC day. Ledger is the source of truth."""
    d = day or _utc_day()
    records = _read_records(ledger_path)
    calls = served = blocked = 0
    usd = 0.0
    for rec in records:
        if _utc_day(rec.get("observed_at")) != d:
            continue
        calls += 1
        gr = str(rec.get("gate_result"))
        if gr == ALLOWED:
            served += 1
            usd += _record_spend(rec)
        elif gr in (BLOCKED_BUDGET, BLOCKED_FAILCLOSED):
            blocked += 1
    return {
        "date": d,
        "calls": calls,
        "served": served,
        "blocked": blocked,
        "usd": round(usd, 6),
        "source": "derived_from_ledger",
        "retention_note": "ledger retained 90 days, then archived (design §2.4); rollup is a cache",
    }


def _spend_before(ledger_path: Optional[Path], scope: str, key: str) -> float:
    """Sum served spend within a scope ('day'|'month') matching key. Raises LedgerError."""
    records = _read_records(ledger_path)
    total = 0.0
    for rec in records:
        ts = rec.get("observed_at")
        match = _utc_day(ts) == key if scope == "day" else _utc_month(ts) == key
        if match:
            total += _record_spend(rec)
    return round(total, 6)


# --------------------------------------------------------------------------- gate

def _staged_verdict(provider: str, estimated: Optional[float], snapshot: Dict[str, Any],
                    reason: str) -> Dict[str, Any]:
    """DOORSTEP-shaped staged verdict — NOT_EXECUTED. Never creates founder-queue entries."""
    return {
        "schema": STAGE_SCHEMA,
        "kind": "budget_doorstep",
        "staged_at": _now(),
        "status": "STAGED",
        "execution": "NOT_EXECUTED",
        "gate": "DOORSTEP",
        "provider": provider,
        "estimated_cost_usd": estimated,
        "budget_snapshot": snapshot,
        "reason": reason,
        "speech_text": "Voice budget reached; approve additional spend on the doorstep.",
        "note": (
            "Paid voice stages at the founder door like deploy/spend/keys. Voice never raises a "
            "budget ceiling — that stays a founder-only YAML/env edit."
        ),
    }


def preflight_cost_gate(
    billable_chars: int,
    provider: str = "elevenlabs",
    *,
    policy: Optional[Dict[str, Any]] = None,
    ledger_path: Optional[Path] = None,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Fail-closed pre-flight gate for a single paid TTS call.

    Returns a verdict dict:
      allow, gate_result, reason, estimated_cost_usd, price_unknown, doorstep,
      fallback, budget_snapshot, staged (or None), ledger_record.
    The caller writes `ledger_record` to the usage ledger (fail-closed on write failure).
    """
    ts = now or _now()
    p = policy if policy is not None else load_voice_policy()
    cfg = cost_config(p)
    chars = max(0, int(billable_chars or 0))
    estimated, price_unknown, rate = estimate_cost_usd(chars, provider, p)

    # local_tts (and any FREE provider): always available, never gated, zero cost.
    if provider in FREE_PROVIDERS:
        return _verdict(
            allow=True, gate_result=ALLOWED, reason="free_provider", provider=provider,
            chars=chars, estimated=0.0, price_unknown=False, doorstep=False,
            snapshot=_snapshot(cfg, 0.0, 0.0), ts=ts, fallback_from=None,
        )

    # Read spend snapshot (fail-closed if the ledger exists but is unreadable).
    ledger_unreadable = False
    day_spend = month_spend = 0.0
    try:
        day_spend = _spend_before(ledger_path, "day", _utc_day(ts))
        month_spend = _spend_before(ledger_path, "month", _utc_month(ts))
    except LedgerError:
        ledger_unreadable = True

    snapshot = _snapshot(cfg, day_spend, month_spend)

    def _blocked(gate_result: str, reason: str, doorstep: bool) -> Dict[str, Any]:
        staged = None
        if doorstep and cfg["doorstep_on_budget_exhaustion"]:
            staged = _staged_verdict(provider, estimated, snapshot, reason)
        return _verdict(
            allow=False, gate_result=gate_result, reason=reason, provider=provider,
            chars=chars, estimated=estimated, price_unknown=price_unknown,
            doorstep=bool(doorstep and cfg["doorstep_on_budget_exhaustion"]),
            snapshot=snapshot, ts=ts, fallback_from=provider, staged=staged,
        )

    # --- fail-closed ordering ---
    if not cfg["cost_enabled"]:
        return _blocked(BLOCKED_FAILCLOSED, "cost_disabled", doorstep=False)
    if price_unknown:
        return _blocked(BLOCKED_FAILCLOSED, "provider_price_unknown", doorstep=False)
    if ledger_unreadable:
        return _blocked(BLOCKED_FAILCLOSED, "ledger_unreadable", doorstep=False)

    est = float(estimated or 0.0)
    if est > cfg["per_call_ceiling_usd"]:
        return _blocked(BLOCKED_BUDGET, "per_call_ceiling", doorstep=True)
    if day_spend + est > cfg["daily_budget_usd"]:
        return _blocked(BLOCKED_BUDGET, "daily_budget", doorstep=True)
    if month_spend + est > cfg["monthly_budget_usd"]:
        return _blocked(BLOCKED_BUDGET, "monthly_budget", doorstep=True)

    return _verdict(
        allow=True, gate_result=ALLOWED, reason="within_budget", provider=provider,
        chars=chars, estimated=est, price_unknown=False, doorstep=False,
        snapshot=snapshot, ts=ts, fallback_from=None,
    )


def _snapshot(cfg: Dict[str, Any], day_spend: float, month_spend: float) -> Dict[str, Any]:
    return {
        "daily_spend_before_usd": round(day_spend, 6),
        "daily_budget_usd": cfg["daily_budget_usd"],
        "month_spend_before_usd": round(month_spend, 6),
        "monthly_budget_usd": cfg["monthly_budget_usd"],
        "per_call_ceiling_usd": cfg["per_call_ceiling_usd"],
        "cost_enabled": cfg["cost_enabled"],
    }


def _verdict(
    *,
    allow: bool,
    gate_result: str,
    reason: str,
    provider: str,
    chars: int,
    estimated: Optional[float],
    price_unknown: bool,
    doorstep: bool,
    snapshot: Dict[str, Any],
    ts: str,
    fallback_from: Optional[str],
    staged: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ledger_record = {
        "schema": USAGE_SCHEMA,
        "observed_at": ts,
        "provider": provider,
        "mode": "TTS",
        "billable_chars": chars,
        "estimated_cost_usd": estimated,
        # ElevenLabs urllib path returns no per-call billed cost => UNKNOWN (null). Estimate is
        # the accounting basis; discrepancies are surfaced, not hidden (no_fake_green).
        "actual_cost_usd": None,
        "gate_result": gate_result,
        "reason": reason,
        "budget_snapshot": snapshot,
        "fallback_from": fallback_from,
        "price_unknown": price_unknown,
        "redacted": True,  # never store raw text, keys, or secrets
    }
    return {
        "allow": allow,
        "gate_result": gate_result,
        "reason": reason,
        "provider": provider,
        "billable_chars": chars,
        "estimated_cost_usd": estimated,
        "price_unknown": price_unknown,
        "doorstep": doorstep,
        "fallback": "local_tts",
        "budget_snapshot": snapshot,
        "staged": staged,
        "ledger_record": ledger_record,
    }


def write_staging_artifact(
    staged_verdict: Dict[str, Any],
    staging_dir: Optional[Path] = None,
) -> Path:
    """Optionally persist a budget-doorstep staged artifact (execution: NOT_EXECUTED).

    Not called on the live paid path by default (to avoid cluttering the running soak); the
    verdict is returned/recorded instead. Exposed so the DOORSTEP staging shape is testable and
    so an operator flow can persist it under artifacts/voice/staging/ on demand.
    """
    if staging_dir is not None:
        dest = Path(staging_dir)
    else:
        from backend.voice.policy import staging_dir as _sd

        dest = _sd()
    dest.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = dest / f"budget_doorstep_{ts}.json"
    path.write_text(json.dumps(staged_verdict, indent=2), encoding="utf-8")
    return path
