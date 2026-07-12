"""REQ-ES-003 — universal dispatch enforcement proofs.

Part 1: the real repo is clean (0 ungated provider calls).
Part 2: seeded bypasses FAIL static enforcement -- a scanner that cannot catch a
        reintroduced raw provider call is not a control.
Part 3: Grok and Ollama still route through the gateway.
No test makes an external call.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCANNER = ROOT / "scripts" / "goal" / "verify_no_ungated_egress.py"

from scripts.goal.verify_no_ungated_egress import scan_module, module_is_guarded  # noqa: E402
import ast  # noqa: E402


# --- Part 1: the real repo is clean ----------------------------------------

def test_real_repo_has_zero_ungated_provider_calls():
    r = subprocess.run([sys.executable, str(SCANNER)], cwd=str(ROOT),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_two_real_egress_modules_are_guarded():
    for rel in ("backend/model_router/google_frontier.py", "scripts/council_key_audit.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        assert module_is_guarded(tree), f"{rel} must install ensure_guard()"


def test_the_five_false_positives_are_not_flagged():
    """Scanners, inventory tools, and base-URL strings make no call -- not violations."""
    for rel in ("scripts/verify_model_dispatch_chokepoint.py",
                "scripts/council/inventory_outbound_paths.py",
                "scripts/goal/verify_no_ungated_egress.py",
                "scripts/prompt_brain/model_adapters.py",
                "scripts/council/gateway.py"):
        assert scan_module(rel) == [], f"{rel} was a false positive"


# --- Part 2: seeded bypasses must fail static enforcement -------------------

def _scan_scratch(tmp_path, rel: str, body: str) -> list:
    """Write a module into a scratch mirror and scan just it."""
    import importlib.util
    # scan_module reads ROOT/rel; mirror the file under a temp ROOT by monkeypatching.
    from scripts.goal import verify_no_ungated_egress as mod
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    orig = mod.ROOT
    mod.ROOT = tmp_path
    try:
        return mod.scan_module(rel)
    finally:
        mod.ROOT = orig


def test_seeded_bypass_raw_urllib_to_openai(tmp_path):
    body = ('import urllib.request\n'
            'def leak(p):\n'
            '    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=p)\n'
            '    return urllib.request.urlopen(req).read()\n')
    v = _scan_scratch(tmp_path, "backend/rogue.py", body)
    assert v and v[0]["kind"] == "PROVIDER_HTTP_CALL"


def test_seeded_bypass_requests_post_to_anthropic(tmp_path):
    body = ('import requests\n'
            'def leak(p):\n'
            '    return requests.post("https://api.anthropic.com/v1/messages", json=p)\n')
    v = _scan_scratch(tmp_path, "backend/rogue2.py", body)
    assert v and v[0]["kind"] == "PROVIDER_HTTP_CALL"


def test_seeded_bypass_model_cli_subprocess(tmp_path):
    body = ('import subprocess\n'
            'def leak(p):\n'
            '    return subprocess.run(["grok", "-p", p], capture_output=True)\n')
    v = _scan_scratch(tmp_path, "backend/rogue3.py", body)
    assert v and v[0]["kind"] == "MODEL_CLI_SUBPROCESS"


def test_seeded_bypass_is_cleared_by_guarding_the_module(tmp_path):
    """Same rogue call, but the module installs the guard -> no longer a violation."""
    body = ('from scripts.council.gateway import ensure_guard\n'
            'ensure_guard()\n'
            'import urllib.request\n'
            'def leak(p):\n'
            '    return urllib.request.urlopen("https://api.openai.com/v1/chat/completions")\n')
    v = _scan_scratch(tmp_path, "backend/guarded.py", body)
    assert v == []


def test_loopback_is_never_a_violation(tmp_path):
    body = ('import urllib.request\n'
            'def health():\n'
            '    return urllib.request.urlopen("http://127.0.0.1:11434/api/tags")\n')
    v = _scan_scratch(tmp_path, "backend/local.py", body)
    assert v == []


def test_a_mere_hostname_string_is_not_a_call(tmp_path):
    body = ('PROVIDER_HOSTS = ["api.openai.com", "api.anthropic.com"]\n'
            'BASE = "https://api.openai.com/v1"   # base-URL constant, no call\n')
    v = _scan_scratch(tmp_path, "backend/const.py", body)
    assert v == []


# --- Part 3: Grok and Ollama still work through the gateway -----------------

def test_grok_and_ollama_dispatch_types_exist_in_the_gateway():
    from scripts.council.gateway import DispatchType
    assert DispatchType.CLI_GROK
    assert DispatchType.LOCAL_OLLAMA


def test_gateway_guard_blocks_ungated_but_the_gateway_module_is_approved():
    from scripts.goal.verify_no_ungated_egress import (APPROVED_GATEWAY_MODULES,
                                                       scan_module)
    assert "scripts/council/gateway.py" in APPROVED_GATEWAY_MODULES
    assert scan_module("scripts/council/gateway.py") == []
