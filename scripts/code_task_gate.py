"""Code task gate — fail-closed compile + test verification for code-class agent tasks.

This module closes handoff item `a-codeloop-wire`: `backend/agent_executor.py` has long
imported it under `if ALLOW_CODE and tclass == "code"`, but the module was never delivered
(a fake-green gap). The two consumed entry points and their exact contracts are:

  * compile_check(path) -> (ok: bool, msg: str)
      agent_executor.py `_verify_compile` (~L429-430):
          from scripts.code_task_gate import compile_check
          ok, msg = compile_check(str(p))
      `p` is an already-resolved absolute Path. Returns a (bool, message) tuple.

  * gate(path, spec, cwd=None) -> dict
      agent_executor.py `execute_task` (~L620-637):
          from scripts.code_task_gate import gate as code_gate
          gate_res = code_gate(fpath, {"tests": spec.get("pytest")}, cwd=str(ROOT))
          if not gate_res.get("verified"): hint = gate_res.get("retry_hint", "verification failed")
      `fpath` is a repo-relative path; `spec["tests"]` is a pytest target (str) or None.
      The caller consumes `verified` (bool) and `retry_hint` (str). We return those plus
      extra diagnostic keys.

DOCTRINE — NO FAKE GREEN / FAIL-CLOSED:
  Every branch that cannot POSITIVELY prove success resolves to a non-pass verdict.
  Missing file, non-clean compile, missing tests, no tests collected, failing tests,
  timeout, or any unexpected exception => verified=False. `verified` is only ever True
  after a clean compile AND a pytest run that exited 0 with at least one test collected.

Standard library only (py_compile / ast for compile, subprocess + pytest for the test stage).
"""
from __future__ import annotations

import ast
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Test stage wall-clock budget. Fail-closed on overrun.
TEST_TIMEOUT = int(os.environ.get("CODE_GATE_TEST_TIMEOUT", "600"))


def _resolve(path: str, cwd: Optional[str]) -> Path:
    """Resolve `path` against `cwd` when it is relative; leave absolute paths as-is."""
    p = Path(path)
    if not p.is_absolute() and cwd:
        p = Path(cwd) / p
    return p


def compile_check(path: str) -> "tuple[bool, str]":
    """Verify a source file compiles. Returns (ok, message).

    FAIL-CLOSED: a missing file, a syntax error, or any unexpected failure returns
    (False, msg). Non-Python files have nothing to byte-compile and are reported as a
    skipped-but-ok check, mirroring the caller's own `_verify_compile` fallback contract.
    """
    try:
        p = Path(path)
        if not p.exists():
            return False, f"compile target missing: {path}"
        if p.suffix != ".py":
            return True, f"{path} (non-python, compile check skipped)"
        src = p.read_text(encoding="utf-8", errors="replace")
        # ast.parse gives a clean, precise SyntaxError before byte-compilation.
        try:
            ast.parse(src, filename=str(p))
        except SyntaxError as e:
            return False, f"syntax error in {path}: line {e.lineno}: {e.msg}"
        # py_compile is the belt-and-suspenders check (catches anything ast missed).
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            return False, f"py_compile failed for {path}: {str(e)[:300]}"
        return True, f"{path}: compiles clean"
    except Exception as e:  # fail-closed on anything unexpected
        return False, f"compile_check error for {path}: {type(e).__name__}: {str(e)[:200]}"


def _run_pytest(target: str, cwd: Optional[str]) -> "tuple[bool, int, str]":
    """Run pytest on `target`. Returns (passed, returncode, tail). FAIL-CLOSED on any error.

    Only pytest exit code 0 (all collected tests passed) counts as a pass. Code 5
    (no tests collected) is treated as FAIL — an unverifiable task is not a passing one.
    """
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", target, "-q"],
            cwd=cwd, capture_output=True, text=True, timeout=TEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, -1, f"pytest {target}: TIMEOUT after {TEST_TIMEOUT}s"
    except Exception as e:
        return False, -2, f"pytest {target}: run error: {type(e).__name__}: {str(e)[:200]}"
    tail = (r.stdout + "\n" + r.stderr).strip()[-500:]
    if r.returncode == 5:
        return False, 5, f"pytest {target}: NO TESTS COLLECTED (fail-closed)\n{tail}"
    if r.returncode == 0:
        return True, 0, f"pytest {target}: PASS\n{tail}"
    return False, r.returncode, f"pytest {target}: FAIL (exit {r.returncode})\n{tail}"


def gate(path: str, spec: Optional[dict] = None, cwd: Optional[str] = None) -> dict:
    """Full code-task verdict: compile the artifact, then require a passing pytest target.

    FAIL-CLOSED contract — `verified` is True ONLY when:
      1. `path` compiles clean, AND
      2. `spec["tests"]` names a pytest target that runs and exits 0 with >=1 test.
    A missing test target is an explicit failure: a code task with nothing to prove it
    works does not pass.

    Returns a dict consumed by agent_executor.execute_task:
      { "verified": bool, "retry_hint": str, "compile_ok": bool, "tests_ok": bool,
        "stage": str, "detail": str, "path": str }
    """
    spec = spec or {}
    resolved = _resolve(path, cwd)

    # Stage 1 — compile.
    compile_ok, compile_msg = compile_check(str(resolved))
    if not compile_ok:
        return {
            "verified": False, "retry_hint": compile_msg, "compile_ok": False,
            "tests_ok": False, "stage": "compile", "detail": compile_msg, "path": path,
        }

    # Stage 2 — tests. Missing test target => fail-closed.
    tests_target = spec.get("tests")
    if not tests_target:
        hint = (f"no test target for code task {path}: a code result must ship a passing "
                f"pytest target to be verified (fail-closed)")
        return {
            "verified": False, "retry_hint": hint, "compile_ok": True,
            "tests_ok": False, "stage": "tests", "detail": hint, "path": path,
        }

    tests_ok, code, test_msg = _run_pytest(str(tests_target), cwd)
    if not tests_ok:
        return {
            "verified": False, "retry_hint": test_msg, "compile_ok": True,
            "tests_ok": False, "stage": "tests", "detail": test_msg, "path": path,
        }

    return {
        "verified": True, "retry_hint": "", "compile_ok": True, "tests_ok": True,
        "stage": "done", "detail": f"{compile_msg}; {test_msg}", "path": path,
    }
