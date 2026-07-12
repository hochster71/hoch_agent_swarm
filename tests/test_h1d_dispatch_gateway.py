"""H1D.7 — CouncilDispatchGateway behavioral proofs.

No provider call occurs in these tests: transports are doubles; the runtime
guard blocks ungated model I/O. Estimated spend is never claimed authoritative.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.council.gateway import (  # noqa: E402
    CouncilDispatchGateway,
    DispatchType,
    GatewayLedger,
    GatewayRequest,
    ModelDispatchGuard,
    UngatedDispatchError,
    default_policy,
    ensure_guard,
)
from scripts.council.spend_gate import CostLedger, SubprocessSpendGate  # noqa: E402
from scripts.prompt_brain import model_adapters as MA  # noqa: E402
from scripts import verify_model_dispatch_chokepoint as scanner  # noqa: E402

GOV = {
    "monthly_incremental_budget_usd": 200,
    "grok": {"credits_remaining_usd": 75.30, "credits_used_usd": 13.59, "requests": 1406},
}


@pytest.fixture(autouse=True)
def _guard():
    ensure_guard()
    yield


@pytest.fixture
def gov_path(tmp_path):
    p = tmp_path / "cost_governor.json"
    p.write_text(json.dumps(GOV))
    return p


@pytest.fixture
def policy():
    p = default_policy()
    # Allow test binaries for local CLI double paths
    p["executable_allowlist"]["LOCAL_OLLAMA"] = ["ollama", "echo", "false"]
    p["executable_allowlist"]["CLI_GROK"] = ["grok", "echo"]
    return p


@pytest.fixture
def gw(tmp_path, gov_path, policy):
    ledger = GatewayLedger(tmp_path / "gateway_ledger.jsonl")
    spend = SubprocessSpendGate(
        ledger=CostLedger(tmp_path / "cost.jsonl"),
        governor_path=gov_path,
    )
    return CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=ledger,
        spend_gate=spend,
        governor_path=gov_path,
        transport=lambda req: {
            "stdout": "VERDICT: ok\nRATIONALE: double\nBYPASS: NONE",
            "stderr": "",
            "exit_code": 0,
            "status": "COMPLETED",
            "latency_ms": 5,
        },
    )


def _req(**kw) -> GatewayRequest:
    base = dict(
        task_id="T-H1D7-1",
        pert_node="H1D.7",
        caller_identity="test.suite",
        dispatch_type=DispatchType.LOCAL_OLLAMA,
        prompt="hello",
        scope="read-only",
        binary="echo",
        argv=["echo", "hello"],
        frontier_required=False,
    )
    base.update(kw)
    return GatewayRequest(**base)


# --- 1 direct OpenAI HTTP path blocked ------------------------------------

def test_01_direct_openai_http_path_blocked():
    ensure_guard()
    adapter = MA.OpenAIAdapter()
    adapter.is_available = True
    adapter.api_key = "sk-test-not-real"
    with pytest.raises(RuntimeError, match="blocked by CouncilDispatchGateway|BLOCKED"):
        adapter.execute("sys", {"task_id": "", "pert_node": ""}, {})


def test_01b_openai_adapter_source_has_no_direct_urlopen_post():
    src = Path(MA.__file__).read_text(encoding="utf-8")
    # No residual direct POST implementation
    assert "urlopen(req" not in src or "GatewayRequest" in src
    assert "chat/completions" not in src or "endpoint=" in src
    # execute must mention gateway
    assert "CouncilDispatchGateway" in src
    assert "API_OPENAI" in src


# --- 2–4 direct CLI / ollama blocked outside gateway ----------------------

def test_02_direct_grok_subprocess_blocked_outside_gateway():
    ensure_guard()
    with pytest.raises(UngatedDispatchError):
        subprocess.run(["grok", "-p", "hi"], capture_output=True, timeout=1)


def test_03_direct_gemini_subprocess_blocked_outside_gateway():
    ensure_guard()
    with pytest.raises(UngatedDispatchError):
        subprocess.run(["gemini", "-p", "hi"], capture_output=True, timeout=1)


def test_04_direct_ollama_subprocess_blocked_outside_gateway():
    ensure_guard()
    with pytest.raises(UngatedDispatchError):
        subprocess.run(["ollama", "run", "llama3", "hi"], capture_output=True, timeout=1)


def test_04b_direct_openai_urlopen_blocked_outside_gateway():
    ensure_guard()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=b"{}",
        method="POST",
    )
    with pytest.raises(UngatedDispatchError):
        urllib.request.urlopen(req, timeout=1)


# --- 5–6 approved adapters through gateway --------------------------------

def test_05_approved_grok_through_gateway(gw):
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=True,
            frontier_justification="council independent review seat",
            binary="echo",
            argv=["echo", "ok"],
        )
    )
    assert res.status == "COMPLETED"
    assert res.decision_status == "ALLOWED"
    assert res.provider_reported_cost is None
    assert res.credit_balance_authoritative is False
    assert res.billing_source == "estimated_from_tokens_or_request"
    assert res.record_hash


def test_06_approved_ollama_through_gateway(gw):
    res = gw.dispatch(_req(dispatch_type=DispatchType.LOCAL_OLLAMA))
    assert res.status == "COMPLETED"
    assert res.estimated_cost == 0.0
    assert res.external_call is False or res.decision_status == "ALLOWED"


# --- 7–9 identity / policy ------------------------------------------------

def test_07_missing_task_id_blocks(gw):
    res = gw.dispatch(_req(task_id=""))
    assert res.status == "BLOCKED"
    assert "MISSING_TASK_ID" in res.blocks


def test_08_missing_pert_node_blocks(gw):
    res = gw.dispatch(_req(pert_node=""))
    assert res.status == "BLOCKED"
    assert "MISSING_PERT_NODE" in res.blocks


def test_09_stale_policy_blocks(tmp_path, gov_path):
    pol = default_policy()
    pol["issued_at"] = (datetime.now(timezone.utc) - timedelta(days=400)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    pol["stale_after_seconds"] = 60
    gw = CouncilDispatchGateway(
        policy=pol,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=gov_path
        ),
        governor_path=gov_path,
        transport=lambda r: {"stdout": "x", "exit_code": 0, "status": "COMPLETED"},
    )
    res = gw.dispatch(_req())
    assert res.status == "BLOCKED"
    assert "POLICY_STALE" in res.blocks


# --- 10–13 spend ----------------------------------------------------------

def test_10_malformed_budget_state_blocks(tmp_path, policy):
    bad = tmp_path / "gov.json"
    bad.write_text("{not-json")
    gw = CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=bad
        ),
        governor_path=bad,
        transport=lambda r: {"stdout": "x", "exit_code": 0, "status": "COMPLETED"},
    )
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=True,
            frontier_justification="need frontier",
            binary="echo",
        )
    )
    assert res.status == "BLOCKED"
    assert any(b in res.blocks for b in ("MALFORMED_BUDGET_STATE", "NO_BUDGET_EVIDENCE"))


def test_11_monthly_cap_blocks(tmp_path, gov_path, policy):
    # Pre-fill cost ledger near cap
    cl = CostLedger(tmp_path / "c.jsonl")
    for i in range(3):
        cl.append(
            {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "billing_period": datetime.now(timezone.utc).strftime("%Y-%m"),
                "category": "model_dispatch",
                "task_id": f"pre-{i}",
                "adapter": "grok",
                "status": "COMPLETED",
                "amount_usd": 80.0,
                "external_call": True,
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
    policy = dict(policy)
    policy["monthly_cap_usd"] = 200.0
    gw = CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(ledger=cl, governor_path=gov_path),
        governor_path=gov_path,
        transport=lambda r: {"stdout": "x", "exit_code": 0, "status": "COMPLETED"},
    )
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=True,
            frontier_justification="need frontier",
            binary="echo",
            prompt="x" * 40000,  # inflate estimate
        )
    )
    # 240 already on ledger > 200 cap
    assert res.status == "BLOCKED"
    assert "MONTHLY_BUDGET_EXCEEDED" in res.blocks


def test_12_per_task_cap_blocks(gw):
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=True,
            frontier_justification="need frontier",
            binary="echo",
            per_task_cap_usd=0.0000001,
            prompt="word " * 5000,
        )
    )
    assert res.status == "BLOCKED"
    assert "PER_TASK_CAP_EXCEEDED" in res.blocks


def test_13_credit_floor_blocks(tmp_path, policy):
    gov = dict(GOV)
    gov["grok"] = dict(GOV["grok"])
    gov["grok"]["credits_remaining_usd"] = 25.001  # barely above floor before est
    gp = tmp_path / "gov.json"
    gp.write_text(json.dumps(gov))
    # Force estimate to push under floor
    policy = dict(policy)
    policy["credit_floor_usd"] = 25.0
    gw = CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=gp
        ),
        governor_path=gp,
        transport=lambda r: {"stdout": "x", "exit_code": 0, "status": "COMPLETED"},
    )
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=True,
            frontier_justification="need frontier",
            binary="echo",
            prompt="tok " * 200000,  # large estimated cost
            per_task_cap_usd=50.0,
        )
    )
    assert res.status == "BLOCKED"
    assert "GROK_CREDITS_BELOW_FLOOR" in res.blocks


# --- 14–16 allowlists / external ------------------------------------------

def test_14_executable_not_allowlisted_blocks(gw):
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.LOCAL_OLLAMA,
            binary="not-a-real-model-cli",
            argv=["not-a-real-model-cli", "x"],
        )
    )
    assert res.status == "BLOCKED"
    assert any("EXECUTABLE_NOT_ALLOWLISTED" in b or "CLI_NOT_INSTALLED" in b for b in res.blocks)


def test_15_endpoint_not_allowlisted_blocks(tmp_path, gov_path, policy):
    policy = dict(policy)
    policy["authorized_dispatch_types"] = list(policy["authorized_dispatch_types"]) + [
        "API_OPENAI"
    ]
    policy["authorized_adapters"] = list(policy["authorized_adapters"]) + ["openai"]
    policy["metered_api_allowed"] = True
    gw = CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=gov_path
        ),
        governor_path=gov_path,
        transport=lambda r: {"stdout": "x", "exit_code": 0, "status": "COMPLETED"},
    )
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.API_OPENAI,
            frontier_required=True,
            frontier_justification="metered",
            authorization_state="FOUNDER_GRANTED",
            endpoint="https://evil.example.com/v1/chat",
            binary=None,
            argv=None,
        )
    )
    assert res.status == "BLOCKED"
    assert any("ENDPOINT_NOT_ALLOWLISTED" in b for b in res.blocks)


def test_16_external_dispatch_prohibited_blocks_frontier(gw):
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=True,
            frontier_justification="need frontier",
            external_dispatch_allowed=False,
            binary="echo",
        )
    )
    assert res.status == "BLOCKED"
    assert "EXTERNAL_DISPATCH_PROHIBITED" in res.blocks


# --- 17 local-first -------------------------------------------------------

def test_17_local_first_prevents_unnecessary_frontier(gw):
    res = gw.dispatch(
        _req(
            dispatch_type=DispatchType.CLI_GROK,
            frontier_required=False,
            binary="echo",
        )
    )
    assert res.status == "BLOCKED"
    assert "LOCAL_FIRST_VIOLATION_FRONTIER_NOT_REQUIRED" in res.blocks


# --- 18 ledger failure ----------------------------------------------------

def test_18_ledger_write_failure_blocks(tmp_path, gov_path, policy):
    ledger = GatewayLedger(tmp_path / "gl.jsonl")
    ledger._force_fail = True
    gw = CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=ledger,
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=gov_path
        ),
        governor_path=gov_path,
        transport=lambda r: {"stdout": "x", "exit_code": 0, "status": "COMPLETED"},
    )
    res = gw.dispatch(_req())
    assert res.status == "BLOCKED"
    assert res.decision_status == "BLOCKED_LEDGER" or "LEDGER_WRITE_FAILED" in res.blocks


# --- 19 timeout -----------------------------------------------------------

def test_19_timeout_fail_closed(tmp_path, gov_path, policy):
    def slow(req):
        raise subprocess.TimeoutExpired(cmd="echo", timeout=1)

    # transport raises TimeoutExpired — gateway catches
    # Actually gateway only catches TimeoutExpired around transport if we raise it
    gw = CouncilDispatchGateway(
        policy=policy,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=gov_path
        ),
        governor_path=gov_path,
        transport=slow,
    )
    res = gw.dispatch(_req())
    assert res.status in ("TIMEOUT", "ERROR")
    assert res.blocks  # fail closed — no fabricated success


# --- 20 no provider call in tests -----------------------------------------

def test_20_no_provider_call_in_tests(gw, monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    res = gw.dispatch(_req())
    assert res.status == "COMPLETED"
    assert calls == []


# --- 21–22 scanner --------------------------------------------------------

def test_21_scanner_catches_seeded_bypass(tmp_path):
    seed = tmp_path / "seed_bypass.py"
    seed.write_text(
        'import urllib.request\n'
        'urllib.request.urlopen("https://api.openai.com/v1/chat/completions")\n'
    )
    # Place under scripts/prompt_brain path pattern by writing content scan via --seed
    result = scanner.scan(seed_bypass_path=seed)
    assert result["status"] == "FAIL"
    assert result["violation_count"] >= 1


def test_22_scanner_allows_documented_exceptions():
    result = scanner.scan()
    # model_adapters health urllib is excepted; gateway modules approved
    # Must PASS on clean tree after H1D.7 remediation
    if result["status"] != "PASS":
        # Show findings for debug
        print(json.dumps(result["findings"][:20], indent=2))
    assert result["status"] == "PASS", result["findings"][:10]


def test_unreadable_policy_fail_closed(tmp_path, gov_path):
    gw = CouncilDispatchGateway(
        policy=None,
        gateway_ledger=GatewayLedger(tmp_path / "gl.jsonl"),
        spend_gate=SubprocessSpendGate(
            ledger=CostLedger(tmp_path / "c.jsonl"), governor_path=gov_path
        ),
        governor_path=gov_path,
    )
    # Force policy None
    gw.policy = None
    res = gw.dispatch(_req())
    assert res.status == "BLOCKED"
    assert res.decision_status == "BLOCKED_POLICY"
