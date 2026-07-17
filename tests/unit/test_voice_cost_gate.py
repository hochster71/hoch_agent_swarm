"""Phase 2 voice cost gate — fail-closed dollar enforcement for paid TTS.

Proves that `daily_budget_usd` (config/voice_policy.yaml) is now ENFORCED, not merely
displayed, and that every fail-closed path degrades to the always-free local_tts floor.

Design: docs/evidence/runtime/voice-sidecar-phase-2-design.md (§1 cost gates, §2 ledger,
§1.5 DOORSTEP tie-in, §3 failure modes, §4 acceptance checklist).

Deliberately imports NO fastapi so the suite runs on the plain system python3 sandbox
(the repo .venv with fastapi is macOS-only).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from backend.voice import cost_gate
from backend.voice import elevenlabs_tts as el


# --------------------------------------------------------------------------- helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_policy(**over):
    """A funded, price-known policy; override individual keys per test."""
    base = {
        "cost_enabled": True,
        "per_call_ceiling_usd": 1.00,
        "daily_budget_usd": 100.0,
        "monthly_budget_usd": 100.0,
        "doorstep_on_budget_exhaustion": True,
        "elevenlabs_usd_per_1k_chars": 0.30,
        "voice_usage_ledger": "data/runtime/voice_usage_ledger.jsonl",
    }
    base.update(over)
    return base


def served_record(usd, ts=None):
    return {
        "schema": cost_gate.USAGE_SCHEMA,
        "observed_at": ts or _now(),
        "provider": "elevenlabs",
        "gate_result": cost_gate.ALLOWED,
        "estimated_cost_usd": usd,
        "actual_cost_usd": None,
        "redacted": True,
    }


# --------------------------------------------------------------------------- estimation
def test_estimate_is_deterministic_and_priced():
    pol = make_policy()
    a = cost_gate.estimate_cost_usd(1000, "elevenlabs", pol)
    b = cost_gate.estimate_cost_usd(1000, "elevenlabs", pol)
    assert a == b
    est, unknown, rate = a
    assert unknown is False
    assert rate == 0.30
    assert est == pytest.approx(0.30)  # 1000 chars * 0.30/1k


def test_free_provider_is_zero_and_never_gated(tmp_path):
    ledger = tmp_path / "u.jsonl"
    v = cost_gate.preflight_cost_gate(5000, "local_tts", policy=make_policy(daily_budget_usd=0),
                                      ledger_path=ledger)
    assert v["allow"] is True
    assert v["estimated_cost_usd"] == 0.0
    assert v["gate_result"] == cost_gate.ALLOWED


# --------------------------------------------------------------------------- allow / ceilings
def test_under_budget_allows(tmp_path):
    ledger = tmp_path / "u.jsonl"
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=make_policy(), ledger_path=ledger)
    assert v["allow"] is True
    assert v["gate_result"] == cost_gate.ALLOWED
    assert v["estimated_cost_usd"] == pytest.approx(0.03)


def test_per_call_ceiling_blocks_even_with_daily_room(tmp_path):
    ledger = tmp_path / "u.jsonl"
    pol = make_policy(per_call_ceiling_usd=0.001, daily_budget_usd=100, monthly_budget_usd=100)
    v = cost_gate.preflight_cost_gate(1000, "elevenlabs", policy=pol, ledger_path=ledger)
    assert v["allow"] is False
    assert v["gate_result"] == cost_gate.BLOCKED_BUDGET
    assert v["reason"] == "per_call_ceiling"
    assert v["fallback"] == "local_tts"


def test_daily_ceiling_blocks_cumulatively(tmp_path):
    ledger = tmp_path / "u.jsonl"
    # Prior served spend of 0.04 today; daily ceiling 0.05.
    cost_gate.append_usage(served_record(0.04), ledger_path=ledger)
    pol = make_policy(daily_budget_usd=0.05, per_call_ceiling_usd=0.05, monthly_budget_usd=100)
    # A ~0.03 call would cross 0.05 -> blocked.
    over = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=pol, ledger_path=ledger)
    assert over["allow"] is False
    assert over["reason"] == "daily_budget"
    # A tiny ~0.003 call still fits under 0.05 -> allowed (prior calls succeed).
    under = cost_gate.preflight_cost_gate(10, "elevenlabs", policy=pol, ledger_path=ledger)
    assert under["allow"] is True


def test_monthly_ceiling_blocks_independently_of_daily(tmp_path):
    ledger = tmp_path / "u.jsonl"
    cost_gate.append_usage(served_record(0.008), ledger_path=ledger)
    pol = make_policy(daily_budget_usd=100, monthly_budget_usd=0.01, per_call_ceiling_usd=100)
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=pol, ledger_path=ledger)
    assert v["allow"] is False
    assert v["reason"] == "monthly_budget"


# --------------------------------------------------------------------------- fail-closed
def test_unknown_price_blocks_failclosed(tmp_path):
    ledger = tmp_path / "u.jsonl"
    pol = make_policy()
    pol.pop("elevenlabs_usd_per_1k_chars")  # price UNKNOWN
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=pol, ledger_path=ledger)
    assert v["allow"] is False
    assert v["price_unknown"] is True
    assert v["gate_result"] == cost_gate.BLOCKED_FAILCLOSED
    assert v["reason"] == "provider_price_unknown"


def test_missing_config_fails_closed(tmp_path):
    ledger = tmp_path / "u.jsonl"
    # Empty policy => cost_config falls to hard fail-closed defaults (disabled, zero budgets).
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy={}, ledger_path=ledger)
    assert v["allow"] is False
    assert v["gate_result"] == cost_gate.BLOCKED_FAILCLOSED
    assert v["reason"] == "cost_disabled"


def test_default_repo_policy_is_failclosed(tmp_path):
    # No policy override => reads the shipped config/voice_policy.yaml, which must block.
    ledger = tmp_path / "u.jsonl"
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", ledger_path=ledger)
    assert v["allow"] is False
    assert v["gate_result"] == cost_gate.BLOCKED_FAILCLOSED


def test_ledger_unreadable_fails_closed(tmp_path):
    ledger = tmp_path / "u.jsonl"
    ledger.write_text("{ this is not valid json\n", encoding="utf-8")
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=make_policy(), ledger_path=ledger)
    assert v["allow"] is False
    assert v["gate_result"] == cost_gate.BLOCKED_FAILCLOSED
    assert v["reason"] == "ledger_unreadable"


# --------------------------------------------------------------------------- ledger + rollup
def test_ledger_append_and_rollup_match_fullscan(tmp_path):
    ledger = tmp_path / "u.jsonl"
    cost_gate.append_usage(served_record(0.01), ledger_path=ledger)
    cost_gate.append_usage(served_record(0.02), ledger_path=ledger)
    blocked = cost_gate.preflight_cost_gate(100, "elevenlabs",
                                            policy=make_policy(daily_budget_usd=0.001),
                                            ledger_path=ledger)
    cost_gate.append_usage(blocked["ledger_record"], ledger_path=ledger)

    roll = cost_gate.daily_rollup(ledger_path=ledger)
    assert roll["served"] == 2
    assert roll["blocked"] == 1
    assert roll["calls"] == 3
    assert roll["usd"] == pytest.approx(0.03)
    # Records contain no raw text / secrets.
    for line in ledger.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        assert rec["schema"] == cost_gate.USAGE_SCHEMA
        assert "speech_text" not in rec and "text" not in rec
        assert rec.get("redacted") is True


# --------------------------------------------------------------------------- DOORSTEP tie-in
def test_budget_exhaustion_stages_at_doorstep(tmp_path):
    ledger = tmp_path / "u.jsonl"
    pol = make_policy(daily_budget_usd=0, doorstep_on_budget_exhaustion=True)
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=pol, ledger_path=ledger)
    assert v["allow"] is False
    assert v["doorstep"] is True
    staged = v["staged"]
    assert staged["execution"] == "NOT_EXECUTED"
    assert staged["gate"] == "DOORSTEP"
    # Optional artifact persists the same NOT_EXECUTED shape under a tmp staging dir.
    path = cost_gate.write_staging_artifact(staged, staging_dir=tmp_path / "staging")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["execution"] == "NOT_EXECUTED"
    assert payload["status"] == "STAGED"


def test_doorstep_can_be_disabled(tmp_path):
    ledger = tmp_path / "u.jsonl"
    pol = make_policy(daily_budget_usd=0, doorstep_on_budget_exhaustion=False)
    v = cost_gate.preflight_cost_gate(100, "elevenlabs", policy=pol, ledger_path=ledger)
    assert v["allow"] is False
    assert v["doorstep"] is False
    assert v["staged"] is None


# --------------------------------------------------------------------------- integration
class _FakeResp:
    def __init__(self, data: bytes):
        self._data = data
        self.headers = {"Content-Type": "audio/mpeg"}

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _force_ready(monkeypatch):
    monkeypatch.setattr(el, "elevenlabs_config_status", lambda: {
        "ready": True, "status": "READY", "blocked_reasons": [],
    })
    monkeypatch.setattr(el, "_api_key", lambda: "sk_test_fake")


def test_synthesize_blocks_on_budget_and_never_calls_network(tmp_path, monkeypatch):
    _force_ready(monkeypatch)
    ledger = tmp_path / "u.jsonl"

    def _boom(*a, **k):
        raise AssertionError("network must NOT be called when the cost gate blocks")

    monkeypatch.setattr(el.urllib.request, "urlopen", _boom)

    pol = make_policy(daily_budget_usd=0)  # enabled but zero budget => block
    ok, meta, audio = el.synthesize_speech("Hello founder, quarterly numbers.",
                                           policy=pol, ledger_path=ledger)
    assert ok is False
    assert audio is None
    assert meta["fallback"] == "local_tts"
    assert meta["status"] == "DOORSTEP"
    # Exactly one BLOCKED record appended, no spend.
    recs = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(recs) == 1
    assert recs[0]["gate_result"] == cost_gate.BLOCKED_BUDGET


def test_synthesize_allows_and_records_when_funded(tmp_path, monkeypatch):
    _force_ready(monkeypatch)
    ledger = tmp_path / "u.jsonl"
    monkeypatch.setattr(el.urllib.request, "urlopen",
                        lambda *a, **k: _FakeResp(b"x" * 500))

    pol = make_policy()  # funded, price known
    ok, meta, audio = el.synthesize_speech("Executive briefing ready.",
                                           policy=pol, ledger_path=ledger)
    assert ok is True
    assert meta["status"] == "LIVE"
    assert meta["provider"] == "elevenlabs"
    assert meta["estimated_cost_usd"] > 0
    recs = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(recs) == 1
    assert recs[0]["gate_result"] == cost_gate.ALLOWED
    assert recs[0].get("actual_cost_usd") is None  # provider does not report per-call cost


def test_synthesize_failcloses_when_ledger_unwritable(tmp_path, monkeypatch):
    _force_ready(monkeypatch)
    ledger = tmp_path / "u.jsonl"

    def _boom(*a, **k):
        raise AssertionError("network must NOT be called when the ledger cannot record spend")

    monkeypatch.setattr(el.urllib.request, "urlopen", _boom)
    # Simulate an unwritable usage ledger (F8): allowed verdict, but the write fails.
    monkeypatch.setattr(cost_gate, "append_usage", lambda *a, **k: False)

    ok, meta, audio = el.synthesize_speech("Fund me.", policy=make_policy(), ledger_path=ledger)
    assert ok is False
    assert audio is None
    assert meta["reason"] == "budget_gate:usage_ledger_unwritable"
    assert meta["fallback"] == "local_tts"
