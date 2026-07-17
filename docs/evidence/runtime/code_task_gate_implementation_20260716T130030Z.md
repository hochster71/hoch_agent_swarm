# Evidence — code_task_gate.py implementation (closes `a-codeloop-wire`)

- **Date (UTC):** 2026-07-16T13:00:30Z
- **Handoff item:** `a-codeloop-wire` — was marked SIGNED but the module was never delivered (fake-green gap). Now closed.
- **Module:** `scripts/code_task_gate.py` (new)
- **Tests:** `tests/test_code_task_gate.py` (new, 9 tests)

## What was built

A fail-closed compile + test gate for code-class agent tasks, standard-library only:
- **compile stage** — `ast.parse` for a precise SyntaxError, then `py_compile.compile(doraise=True)` as a belt-and-suspenders byte-compile.
- **test stage** — `subprocess` runs `python -m pytest <target> -q`. Only exit code 0 (all collected tests passed) counts as a pass; exit 5 (no tests collected), non-zero, timeout, and run errors all resolve to FAIL.

### Fail-closed / NO-FAKE-GREEN behavior
`verified` is True **only** when the artifact compiles clean AND a named pytest target runs and exits 0 with at least one test. Every other branch — missing file, syntax error, missing test target, no tests collected, failing tests, timeout, or any unexpected exception — returns `verified=False` with a non-empty `retry_hint`. A code task that ships no test target is an explicit failure, not a pass.

## Interface matched (exact, against `backend/agent_executor.py`)

Verified by reading the caller; the module was written to fit it, so the caller is **NOT** edited.

1. `compile_check(path) -> (ok: bool, msg: str)`
   - Consumed in `_verify_compile`, `backend/agent_executor.py` ~L429-430:
     ```python
     from scripts.code_task_gate import compile_check
     ok, msg = compile_check(str(p))
     ```
   - `p` is an already-resolved absolute `Path`; return is a `(bool, message)` tuple. Non-Python files report `(True, "…compile check skipped")`, mirroring the caller's own fallback contract (~L434-435).

2. `gate(path, spec, cwd=None) -> dict`
   - Consumed in `execute_task`, `backend/agent_executor.py` ~L618-637 under `if ALLOW_CODE and tclass == "code":`
     ```python
     from scripts.code_task_gate import gate as code_gate
     gate_res = code_gate(fpath, {"tests": spec.get("pytest")}, cwd=str(ROOT))
     if not gate_res.get("verified"):
         hint = gate_res.get("retry_hint", "verification failed")
     ```
   - `fpath` is repo-relative; `spec["tests"]` is a pytest target string or `None`. The caller consumes `verified` (bool) and `retry_hint` (str). We also return `compile_ok`, `tests_ok`, `stage`, `detail`, `path` for diagnostics.

### Smoke check (both call sites, real output)
```
compile_check -> True | scripts/code_task_gate.py: compiles clean
gate keys -> ['compile_ok', 'detail', 'path', 'retry_hint', 'stage', 'tests_ok', 'verified']
gate.verified -> False | retry_hint -> no test target for code task ... (fail-closed)
SMOKE OK: interface matches both call sites
```

## Test run (real output, system python3 in sandbox)

Environment: Python 3.10.12, pytest 9.1.1 (installed into the sandbox; the repo `.venv` is macOS-only and was not touched). Command:

```
$ python3 -m pytest tests/test_code_task_gate.py -q
.........                                                                [100%]
9 passed in 0.58s
```

Coverage of the 9 tests:
- clean Python compiles / passing tests → `verified=True`
- syntax-error code → compile fail
- missing file → fail-closed
- compile-stage failure short-circuits before tests
- no test target / empty spec → fail-closed default (2 tests)
- failing tests → fail
- no tests collected (pytest exit 5) → fail-closed

## Disabled / staged status (founder action required)

The gate is **wired into `agent_executor.py` but DISABLED at runtime.** It only executes inside `if ALLOW_CODE and tclass == "code":`, and `ALLOW_CODE = os.environ.get("AGENT_ALLOW_CODE") == "1"` (`backend/agent_executor.py` L42). `AGENT_ALLOW_CODE` is **not set**. Nothing in the running Phase C soak was touched, no daemon/plist/.env was modified, and code mode was not enabled.

Enabling remains a **founder action**: it requires setting `AGENT_ALLOW_CODE=1` and a **fresh process launch after the soak completes** (the current process read the env at import time). This delivery only removes the fake-green gap by providing the missing, real, tested module so the existing imports resolve; it does not turn anything on.
