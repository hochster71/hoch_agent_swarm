"""Tests for the HOCH Safe-Action Executor gate logic (pure, no side effects)."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hse", REPO / "scripts" / "hoch_safe_executor.py")
hse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hse)


def test_safe_pytest_executes_when_no_hold():
    a = {"id": "t", "requires_michael_approval": False, "category": "verification",
         "exec": {"type": "pytest", "path": "tests/x.py"}}
    verdict, _ = hse.decide(a, hold_cats=set())
    assert verdict == "EXECUTE"


def test_requires_approval_routes_to_approval():
    a = {"id": "t", "requires_michael_approval": True, "exec": {"type": "pytest", "path": "tests/x.py"}}
    verdict, _ = hse.decide(a, hold_cats=set())
    assert verdict == "APPROVAL"


def test_non_whitelisted_type_routes_to_approval():
    a = {"id": "t", "requires_michael_approval": False, "exec": {"type": "shell", "cmd": "echo hi"}}
    verdict, _ = hse.decide(a, hold_cats=set())
    assert verdict == "APPROVAL"


def test_forbidden_term_forces_approval_even_if_type_safe():
    # a 'safe' pytest type but a risky term in the payload -> must NOT auto-run
    a = {"id": "t", "requires_michael_approval": False, "category": "build",
         "exec": {"type": "frontend_build", "note": "then git push and deploy"}}
    verdict, why = hse.decide(a, hold_cats=set())
    assert verdict == "APPROVAL"


def test_operator_hold_blocks_matching_category():
    a = {"id": "t", "requires_michael_approval": False, "category": "release",
         "exec": {"type": "pytest", "path": "tests/x.py"}}
    verdict, _ = hse.decide(a, hold_cats={"release"})
    assert verdict == "BLOCKED"


def test_operator_hold_wildcard_blocks_all():
    a = {"id": "t", "requires_michael_approval": False, "category": "verification",
         "exec": {"type": "pytest", "path": "tests/x.py"}}
    verdict, _ = hse.decide(a, hold_cats={"*"})
    assert verdict == "BLOCKED"


def test_dry_run_has_no_side_effects(tmp_path, monkeypatch):
    # point the queue at a temp file with one safe action; dry-run must not write ledger/approvals
    q = tmp_path / "q.json"
    q.write_text('{"actions":[{"id":"a","title":"t","category":"verification",'
                 '"requires_michael_approval":false,"exec":{"type":"pytest","path":"tests/x.py"}}]}')
    monkeypatch.setattr(hse, "QUEUE", q)
    led = tmp_path / "ledger.jsonl"
    appr = tmp_path / "appr.json"
    monkeypatch.setattr(hse, "LEDGER", led)
    monkeypatch.setattr(hse, "APPROVALS", appr)
    rc = hse.run(dry=True)
    assert rc == 0
    assert not led.exists() and not appr.exists()  # zero side effects in dry-run
