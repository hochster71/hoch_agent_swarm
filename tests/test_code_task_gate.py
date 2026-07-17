"""code_task_gate — fail-closed verification of the code-task compile+test gate.

Closes handoff item `a-codeloop-wire`: `backend/agent_executor.py` imports
`scripts.code_task_gate.compile_check` (~L429) and `scripts.code_task_gate.gate` (~L620)
under `if ALLOW_CODE and tclass == "code"`. These tests pin the exact contracts the
caller consumes and prove the NO-FAKE-GREEN doctrine: nothing that cannot be positively
verified is ever allowed to return a pass.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from scripts.code_task_gate import compile_check, gate


# ---------------------------------------------------------------- helpers
def _write(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


CLEAN_MODULE = """
    def add(a, b):
        return a + b
"""

# A test file that imports the module under test and asserts on it — the passing case.
PASSING_TEST = """
    from mymod import add
    def test_add():
        assert add(2, 3) == 5
"""

# A test file whose assertion is false — the failing-test case.
FAILING_TEST = """
    from mymod import add
    def test_add_wrong():
        assert add(2, 3) == 99
"""


# ---------------------------------------------------------------- compile_check
def test_compile_check_passes_on_clean_python(tmp_path):
    p = _write(tmp_path, "mymod.py", CLEAN_MODULE)
    ok, msg = compile_check(str(p))
    assert ok is True
    assert "compiles clean" in msg


def test_compile_check_fails_on_syntax_error(tmp_path):
    p = _write(tmp_path, "broken.py", "def add(a, b)\n    return a + b\n")  # missing colon
    ok, msg = compile_check(str(p))
    assert ok is False
    assert "syntax error" in msg.lower()


def test_compile_check_fails_closed_on_missing_file(tmp_path):
    ok, msg = compile_check(str(tmp_path / "does_not_exist.py"))
    assert ok is False
    assert "missing" in msg.lower()


# ---------------------------------------------------------------- gate (compile stage)
def test_gate_fails_when_compile_fails(tmp_path):
    p = _write(tmp_path, "broken.py", "def x(:\n    pass\n")
    res = gate("broken.py", {"tests": "test_x.py"}, cwd=str(tmp_path))
    assert res["verified"] is False
    assert res["stage"] == "compile"
    assert res["retry_hint"]  # non-empty hint the caller can surface


# ---------------------------------------------------------------- gate (fail-closed default)
def test_gate_fails_closed_when_no_tests_specified(tmp_path):
    """A code artifact that compiles but ships no test target must NOT pass."""
    _write(tmp_path, "mymod.py", CLEAN_MODULE)
    res = gate("mymod.py", {"tests": None}, cwd=str(tmp_path))
    assert res["verified"] is False
    assert res["compile_ok"] is True
    assert res["tests_ok"] is False
    assert "fail-closed" in res["retry_hint"].lower()


def test_gate_fails_closed_when_spec_is_empty(tmp_path):
    """Empty/absent spec dict is the same as no tests: fail-closed."""
    _write(tmp_path, "mymod.py", CLEAN_MODULE)
    res = gate("mymod.py", {}, cwd=str(tmp_path))
    assert res["verified"] is False
    assert res["tests_ok"] is False


# ---------------------------------------------------------------- gate (test stage)
def test_gate_passes_on_clean_code_with_passing_tests(tmp_path):
    _write(tmp_path, "mymod.py", CLEAN_MODULE)
    _write(tmp_path, "test_mymod.py", PASSING_TEST)
    res = gate("mymod.py", {"tests": "test_mymod.py"}, cwd=str(tmp_path))
    assert res["verified"] is True, res["detail"]
    assert res["compile_ok"] is True
    assert res["tests_ok"] is True
    assert res["retry_hint"] == ""


def test_gate_fails_when_tests_fail(tmp_path):
    _write(tmp_path, "mymod.py", CLEAN_MODULE)
    _write(tmp_path, "test_mymod.py", FAILING_TEST)
    res = gate("mymod.py", {"tests": "test_mymod.py"}, cwd=str(tmp_path))
    assert res["verified"] is False
    assert res["stage"] == "tests"
    assert "FAIL" in res["retry_hint"]


def test_gate_fails_closed_when_no_tests_collected(tmp_path):
    """Pointing at a target with no tests (pytest exit 5) must fail, not silently pass."""
    _write(tmp_path, "mymod.py", CLEAN_MODULE)
    _write(tmp_path, "empty_tests.py", "x = 1  # no test_ functions here\n")
    res = gate("mymod.py", {"tests": "empty_tests.py"}, cwd=str(tmp_path))
    assert res["verified"] is False
    assert "no tests collected" in res["retry_hint"].lower()
