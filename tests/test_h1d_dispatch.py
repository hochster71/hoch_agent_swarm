"""H1D — council dispatch loop proofs.

Runs the REAL router against a stub binary (`echo` / `false`) so the loop, the critic,
the revision cycle, the PERT binding, and the fail-closed paths are all exercised
without spending a cent. The live two-adapter run is a separate, explicit script.

No string literal stands in for a file read (audit F-21.3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.council import dispatch as D  # noqa: E402
from scripts.council.spend_gate import CostLedger, SubprocessSpendGate  # noqa: E402

GOV = {"monthly_incremental_budget_usd": 200,
       "grok": {"credits_remaining_usd": 75.30, "credits_used_usd": 13.59, "requests": 1406}}


class EchoAdapter(D.Adapter):
    """A local stand-in that returns whatever we tell it to. Never external."""
    name = "ollama"
    binary = "echo"
    external = False

    def __init__(self, reply: str):
        self.reply = reply

    def argv(self, task):
        return ["echo", self.reply]


class FailingAdapter(D.Adapter):
    name = "ollama"
    binary = "false"
    external = False

    def argv(self, task):
        return ["false"]


@pytest.fixture
def router(tmp_path):
    gov = tmp_path / "gov.json"
    gov.write_text(json.dumps(GOV))
    gate = SubprocessSpendGate(ledger=CostLedger(tmp_path / "cost.jsonl"),
                               governor_path=gov)
    return D.CouncilRouter(gate=gate, relay_dir=tmp_path / "relay")


def _task(**kw):
    base = dict(task_id="T-1", scope="read-only analysis",
                prompt="State the verdict.",
                evidence_contract=["VERDICT", "RATIONALE"],
                frontier_required=False, pert_node="H1D")
    base.update(kw)
    return D.TaskEnvelope(**base)


# --- critic ----------------------------------------------------------------

def test_critic_rejects_output_missing_required_evidence(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama", EchoAdapter("I think it looks fine"))
    res = router.dispatch_one(_task(), "ollama")
    assert res.status == "COMPLETED"          # the process succeeded...
    assert res.critic_verdict == "REVISE"     # ...but the evidence contract did not
    assert any("MISSING_REQUIRED_EVIDENCE:VERDICT" in r for r in res.critic_reasons)


def test_critic_accepts_only_when_contract_satisfied(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama",
                        EchoAdapter("VERDICT: approve. RATIONALE: it is sound."))
    res = router.dispatch_one(_task(), "ollama")
    assert res.critic_verdict == "ACCEPT"
    assert res.critic_reasons == []


def test_empty_output_is_never_accepted(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama", EchoAdapter(""))
    res = router.dispatch_one(_task(), "ollama")
    assert res.critic_verdict == "REVISE"
    assert "EMPTY_OUTPUT" in res.critic_reasons


def test_failed_adapter_fails_closed_never_fabricates(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama", FailingAdapter())
    res = router.dispatch_one(_task(), "ollama")
    assert res.status == "FAILED"
    assert res.critic_verdict == "REVISE"
    assert res.output == ""                   # no invented result


# --- the automatic revision cycle ------------------------------------------

class FlakyThenGoodAdapter(D.Adapter):
    """Fails the contract first, satisfies it after being told why. No human retypes."""
    name = "ollama"
    binary = "echo"
    external = False

    def argv(self, task):
        if "AUTOMATED COUNCIL REVISION REQUEST" in task.prompt:
            return ["echo", "VERDICT: approve. RATIONALE: corrected after review."]
        return ["echo", "looks good to me"]


def test_one_revision_cycle_happens_automatically(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama", FlakyThenGoodAdapter())
    summary = router.run_council_task(_task(), adapters=["ollama"], max_revisions=1)

    assert summary["attempts"] == 2
    assert summary["revisions_performed"] == 1
    assert summary["accepted_adapters"] == ["ollama"]
    assert summary["manual_copy_paste_operations"] == 0
    # one adapter alone is NOT enough to move the node
    assert summary["pert_node_state"] == "PARTIAL"
    assert summary["pert_node_reason"] == "SINGLE_ADAPTER_ONLY_NO_CORROBORATION"


# --- PERT binding: evidence, not assertion ---------------------------------

def test_pert_node_moves_only_on_two_independent_validated_results(router, monkeypatch):
    good = "VERDICT: approve. RATIONALE: sound."

    class A(EchoAdapter):
        name = "ollama"

    class B(EchoAdapter):
        name = "gemini"
        binary = "echo"
        external = False        # stubbed: no external call in tests

    monkeypatch.setitem(D.ADAPTERS, "ollama", A(good))
    monkeypatch.setitem(D.ADAPTERS, "gemini", B(good))

    # frontier_required=True, otherwise local_first correctly REFUSES the gemini seat
    summary = router.run_council_task(_task(frontier_required=True),
                                      adapters=["ollama", "gemini"])
    assert sorted(summary["accepted_adapters"]) == ["gemini", "ollama"]
    assert summary["pert_node_state"] == "COMPLETED"
    assert summary["pert_node_reason"] == "MULTI_ADAPTER_VALIDATED_EVIDENCE"


def test_pert_node_never_moves_when_no_adapter_satisfies_the_contract(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama", EchoAdapter("nope"))
    summary = router.run_council_task(_task(), adapters=["ollama"], max_revisions=0)
    assert summary["pert_node_state"] == "UNKNOWN"
    assert summary["accepted_adapters"] == []


def test_blocked_adapter_yields_blocked_node_not_a_guess(router):
    # 'openai' is founder-gated: the gate refuses before any spawn
    summary = router.run_council_task(
        _task(frontier_required=True), adapters=["openai"], max_revisions=0)
    assert summary["pert_node_state"] == "BLOCKED"
    assert summary["external_calls"] == 0


# --- the gate is the ONLY spawn point --------------------------------------

def test_no_module_in_the_dispatch_path_spawns_a_subprocess_directly():
    """Only spend_gate.py may call subprocess. dispatch.py must route through it."""
    src = (ROOT / "scripts" / "council" / "dispatch.py").read_text(encoding="utf-8")
    assert "import subprocess" not in src
    assert "subprocess.run" not in src
    assert "os.system" not in src
    assert "Popen" not in src
    # and it must import the gate
    assert "from scripts.council.spend_gate import" in src


def test_every_dispatch_is_hash_ledgered(router, monkeypatch):
    monkeypatch.setitem(D.ADAPTERS, "ollama",
                        EchoAdapter("VERDICT: approve. RATIONALE: ok."))
    router.run_council_task(_task(), adapters=["ollama"])

    lines = [json.loads(l) for l in router.ledger_path.read_text().splitlines() if l.strip()]
    assert lines, "dispatch ledger is empty"
    for e in lines:
        assert e["task_id"] and e["task_digest"]
        assert e["response_sha256"]
        assert e["cost_ledger_hash"]        # binds the dispatch to the SPEND ledger
        assert e["critic_verdict"] in ("ACCEPT", "REVISE", "REJECT")

    ok, errs = router.gate.ledger.verify_chain()
    assert ok, errs
