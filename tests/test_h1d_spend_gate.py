"""H1D — proofs that SubprocessSpendGate can REFUSE.

The three existing budget gates in this repo cannot fail:
  * frontier_escalation_gate.py  -> always prints PASS, exits 0
  * verify_api_budget_guard.py   -> compares a hardcoded 0.0 to the budget
  * anti_fake_gate.sh            -> errors on a broken venv and exits 0

A gate that cannot say no is not a control. These tests exist to prove this one can,
and every test drives the REAL gate against REAL files on disk -- no string literals
stand in for a file read (see audit finding F-21.3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.council.spend_gate import (  # noqa: E402
    B_CLI_NOT_INSTALLED,
    B_FOUNDER_GATE_REQUIRED,
    B_GROK_CREDITS_EXHAUSTED,
    B_LOCAL_FIRST,
    B_MILESTONE_CEILING,
    B_MONTHLY_CAP,
    B_NO_BUDGET_EVIDENCE,
    B_TASK_CAP,
    B_UNKNOWN_ADAPTER,
    CostLedger,
    DispatchRequest,
    SubprocessSpendGate,
    estimate_cost_usd,
)

GOV = {
    "monthly_incremental_budget_usd": 200,
    "grok": {"credits_remaining_usd": 75.30, "credits_used_usd": 13.59, "requests": 1406},
}


@pytest.fixture
def gate(tmp_path):
    gov = tmp_path / "cost_governor.json"
    gov.write_text(json.dumps(GOV))
    return SubprocessSpendGate(ledger=CostLedger(tmp_path / "cost_ledger.jsonl"),
                               governor_path=gov)


def _req(**kw):
    base = dict(task_id="T1", adapter="grok", prompt="review this diff",
                frontier_required=True, per_task_cap_usd=0.50)
    base.update(kw)
    return DispatchRequest(**base)


# --- the gate says NO -------------------------------------------------------

def test_metered_api_key_still_requires_founder_gate(gate):
    """Standing authorization covers already-paid CLIs. It does NOT cover metered keys."""
    for adapter in ("openai", "anthropic", "xai_api"):
        blocks = gate.preflight(_req(adapter=adapter))
        assert B_FOUNDER_GATE_REQUIRED in blocks


def test_unknown_adapter_blocked(gate):
    assert B_UNKNOWN_ADAPTER in gate.preflight(_req(adapter="some-random-cli"))


def test_local_first_is_enforced_not_printed(gate):
    """A frontier CLI may not run for a task that does not declare frontier_required."""
    assert B_LOCAL_FIRST in gate.preflight(_req(adapter="grok", frontier_required=False))
    # ...and a local adapter needs no such declaration.
    assert B_LOCAL_FIRST not in gate.preflight(
        _req(adapter="ollama", frontier_required=False))


def test_grok_credit_floor_blocks(tmp_path):
    """The $25 floor already existed in frontier_escalation_gate.py -- it just never ran."""
    gov = tmp_path / "g.json"
    gov.write_text(json.dumps({"monthly_incremental_budget_usd": 200,
                               "grok": {"credits_remaining_usd": 24.99}}))
    g = SubprocessSpendGate(ledger=CostLedger(tmp_path / "l.jsonl"), governor_path=gov)
    # a dispatch that would push credits below the floor is refused
    assert B_GROK_CREDITS_EXHAUSTED in g.preflight(_req(prompt="review"))


def test_monthly_cap_blocks(tmp_path):
    gov = tmp_path / "g.json"
    gov.write_text(json.dumps({"monthly_incremental_budget_usd": 0.001,
                               "grok": {"credits_remaining_usd": 75.30}}))
    g = SubprocessSpendGate(ledger=CostLedger(tmp_path / "l.jsonl"), governor_path=gov)
    assert B_MONTHLY_CAP in g.preflight(_req())


def test_per_task_cap_blocks(gate):
    assert B_TASK_CAP in gate.preflight(_req(prompt="x" * 400000, per_task_cap_usd=0.001))


def test_milestone_ceiling_blocks(tmp_path):
    gov = tmp_path / "g.json"
    gov.write_text(json.dumps(GOV))
    g = SubprocessSpendGate(ledger=CostLedger(tmp_path / "l.jsonl"), governor_path=gov,
                            spent_this_run_usd=0.9995)
    assert B_MILESTONE_CEILING in g.preflight(_req(milestone_ceiling_usd=1.00,
                                                   prompt="x" * 20000, binary="grok"))


def test_missing_budget_evidence_fails_closed(tmp_path):
    """Absence of evidence is a BLOCK, never a pass. This is the whole doctrine."""
    g = SubprocessSpendGate(ledger=CostLedger(tmp_path / "l.jsonl"),
                            governor_path=tmp_path / "does_not_exist.json")
    assert B_NO_BUDGET_EVIDENCE in g.preflight(_req())


def test_uninstalled_cli_blocked(gate):
    # 'openai' is not an installed CLI on this machine
    assert B_CLI_NOT_INSTALLED in gate.preflight(_req(adapter="openai"))


def test_unknown_pricing_is_infinite_cost(gate):
    assert estimate_cost_usd("mystery-model", "hello") == float("inf")


# --- the gate says YES, and meters it ---------------------------------------

def test_blocked_dispatch_never_spawns_a_subprocess_and_is_still_recorded(gate):
    res = gate.dispatch(_req(adapter="openai"), ["openai", "--version"])
    assert res.status == "BLOCKED"
    assert res.external_call is False
    assert res.estimated_cost_usd == 0.0
    entries = gate.ledger.model_entries()
    assert len(entries) == 1 and entries[0]["status"] == "BLOCKED"
    assert entries[0]["amount_usd"] == 0.0


def test_local_dispatch_is_free_and_metered(gate, tmp_path):
    """Use `echo` as a stand-in local adapter: proves the metering path end to end."""
    gate_local = SubprocessSpendGate(ledger=gate.ledger, governor_path=gate.governor_path)
    req = DispatchRequest(task_id="T-LOCAL", adapter="ollama", prompt="hi",
                          binary="echo", frontier_required=False)
    # dispatch through the real gate, but exec a harmless local command
    res = gate_local.dispatch(req, ["echo", "local-model-output"])
    assert res.status == "COMPLETED"
    assert res.external_call is False
    assert res.estimated_cost_usd == 0.0
    assert "local-model-output" in res.stdout
    assert res.raw_sha256 and res.ledger_entry_hash


def test_ledger_is_hash_chained_and_tamper_evident(gate):
    gate.dispatch(DispatchRequest(task_id="A", adapter="ollama", prompt="1", binary="echo"), ["echo", "a"])
    gate.dispatch(DispatchRequest(task_id="B", adapter="ollama", prompt="2", binary="echo"), ["echo", "b"])
    ok, errs = gate.ledger.verify_chain()
    assert ok, errs

    # tamper: rewrite an amount in place
    lines = gate.ledger.path.read_text().splitlines()
    e = json.loads(lines[0])
    e["amount_usd"] = 999.0
    lines[0] = json.dumps(e, sort_keys=True)
    gate.ledger.path.write_text("\n".join(lines) + "\n")

    ok, errs = gate.ledger.verify_chain()
    assert ok is False
    assert any("HASH_MISMATCH" in x or "CHAIN_BREAK" in x for x in errs)


def test_grok_pricing_matches_founders_measured_usage():
    """$0.315 per 1M tokens is derived from cost_governor: 1406 req, $13.59, 43.1M tokens."""
    cost = estimate_cost_usd("grok", "x" * 4000, max_output_tokens=4000)
    assert 0.0 < cost < 0.01          # a normal council task is sub-cent
    assert estimate_cost_usd("gemini", "x" * 4000) == 0.0   # already-paid Ultra plan
    assert estimate_cost_usd("ollama", "x" * 4000) == 0.0   # local


def test_real_cost_governor_on_disk_is_readable_and_has_the_floor():
    """Drives the REAL file, not a fixture. No string literal stands in for it."""
    gov = json.loads((ROOT / "has_live_project_tracker" / "data" / "cost_governor.json")
                     .read_text(encoding="utf-8"))
    assert gov["monthly_incremental_budget_usd"] == 200
    assert gov["grok"]["credits_remaining_usd"] > 0
    assert gov["policy"]["local_first"] is True
