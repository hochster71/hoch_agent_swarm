"""W1-002c — verifier and burndown provenance. FAILING BY DESIGN.

Pins the exact failure mode discovered 2026-07-20: the tools that compute HELM's
completion percentages age their own evidence by filesystem mtime.

    scripts/verify_runtime_truth_freshness.py:116   ev_mtime = ...st_mtime
    scripts/goal/goal_engine.py:75                  age = time.time() - path.stat().st_mtime
    scripts/goal/verify_champion_gates.py:60        (now - p.stat().st_mtime) / 3600

Consequence: a `git checkout`, `pull`, `stash pop`, or rsync resets the apparent age of
evidence without changing its content, so the burndown can be refreshed by a VCS
operation. Three such operations ran in this repository on 2026-07-20, before the 90%
and 100% figures were read.

Founder-required fixtures:
    produced_at = null, mtime = now  -> verifier does NOT pass; goal engine contributes
                                        zero; champion gate does not turn green
    produced_at = old,  mtime = now  -> verifier STALE/FAIL; burndown cannot count fresh

`HELM_PROMOTION_EVIDENCE_MANIFEST.json` currently carries "produced_at": null on every
entry. Under the corrected model those entries contribute zero and the burndown may
DECREASE. That is the doctrine working, not a regression.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

WEEK = 7 * 86400

SOURCES = {
    "verifier": "scripts/verify_runtime_truth_freshness.py",
    "goal_engine": "scripts/goal/goal_engine.py",
    "champion_gates": "scripts/goal/verify_champion_gates.py",
}


def _src(key: str) -> str:
    p = ROOT / SOURCES[key]
    if not p.exists():
        pytest.skip(f"{SOURCES[key]} absent in this checkout")
    return p.read_text(encoding="utf-8")


def _mtime_age_offenders(src: str) -> list:
    return [
        ln.strip() for ln in src.splitlines()
        if "st_mtime" in ln
        and any(k in ln for k in ("time.time()", "now()", "fresh", "age", "utcfromtimestamp"))
    ]


# --- static: the laundering sites must be gone --------------------------------

@pytest.mark.parametrize("key", list(SOURCES))
def test_no_mtime_derived_evidence_age(key):
    offenders = _mtime_age_offenders(_src(key))
    assert not offenders, (
        f"{SOURCES[key]}: {len(offenders)} site(s) derive evidence age from mtime, "
        "laundering a filesystem timestamp into burndown evidence.\n"
        + "\n".join(f"  {o[:100]}" for o in offenders[:5])
    )


@pytest.mark.parametrize("key", list(SOURCES))
def test_delegates_freshness_to_ratified_contract(key):
    """No parallel freshness implementation — use runtime_truth_contract.is_fresh."""
    src = _src(key)
    assert "runtime_truth_contract" in src or "is_fresh" in src, (
        f"{SOURCES[key]} must delegate freshness evaluation to the ratified contract "
        "rather than computing budgets locally"
    )


# --- behavioural: null produced_at contributes zero ---------------------------

def _contract():
    try:
        from backend.final_verifier.runtime_truth_contract import RuntimeTruthContract
    except Exception:
        pytest.skip("runtime_truth_contract unavailable")
    return RuntimeTruthContract(str(ROOT / "config" / "runtime_truth_contract.json"))


def test_contract_rejects_absent_produced_at_without_raising():
    """is_fresh() takes a float and has no UNKNOWN path. This is the extension point.

    Passing None must yield a not-fresh verdict, not a TypeError and not an
    mtime fallback at the call site.
    """
    c = _contract()
    kinds = list(c.load().get("freshness_budgets_seconds", {}))
    if not kinds:
        pytest.skip("no freshness budgets configured")
    try:
        result = c.is_fresh(kinds[0], None)  # type: ignore[arg-type]
    except TypeError:
        pytest.fail(
            "is_fresh(kind, None) raises TypeError. Callers currently avoid this by "
            "substituting mtime. Extend the contract with an explicit UNKNOWN path "
            "so absent provenance is representable."
        )
    assert result is False, "absent produced_at must never be fresh"


def test_old_produced_at_is_not_fresh_even_with_recent_file():
    c = _contract()
    kinds = list(c.load().get("freshness_budgets_seconds", {}))
    if not kinds:
        pytest.skip("no freshness budgets configured")
    assert c.is_fresh(kinds[0], time.time() - WEEK) is False


def test_unknown_evidence_kind_fails_closed():
    c = _contract()
    assert c.is_fresh("kind-that-does-not-exist", time.time()) is False


# --- manifest: null produced_at must contribute zero --------------------------

def test_promotion_manifest_null_produced_at_is_not_counted_as_fresh():
    p = ROOT / "coordination" / "goal" / "HELM_PROMOTION_EVIDENCE_MANIFEST.json"
    if not p.exists():
        pytest.skip("promotion manifest absent")
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data if isinstance(data, list) else data.get("evidence", data.get("items", []))
    if not isinstance(entries, list) or not entries:
        pytest.skip("manifest shape not recognised")
    nulls = [e for e in entries if isinstance(e, dict) and e.get("produced_at") is None]
    if not nulls:
        return  # producers now populate it — the desired end state
    pytest.fail(
        f"{len(nulls)}/{len(entries)} manifest entries carry produced_at: null. Under "
        "the corrected model each contributes ZERO to the burndown. Repair the "
        "producers (W1-002b/002c evidence-generation), do not infer from mtime. "
        "Expect the headline percentage to fall when this is enforced."
    )


# --- the burndown must be regeneratable from one evidence epoch ---------------

def test_burndown_artifacts_record_their_evidence_epoch():
    """Both burndowns must state the epoch they were computed against."""
    missing = []
    for rel in ("coordination/goal/goal_state.json",
                "coordination/goal/build_to_goal_status.json"):
        p = ROOT / rel
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if not any(k in d for k in ("evidence_epoch", "computed_at", "updated_at")):
            missing.append(rel)
    assert not missing, (
        f"{missing} carry no evidence epoch; two burndowns computed from different "
        "epochs cannot be compared, and differences cannot be explained rather than "
        "concealed"
    )
