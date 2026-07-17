# Code Loop Reliability — the Code Task Gate

**Status:** Delivered · gate DISABLED by default (`AGENT_ALLOW_CODE` unset) · enabling is a founder action
**Owns handoff item:** `a-codeloop-wire`
**Module:** [`scripts/code_task_gate.py`](../../scripts/code_task_gate.py) · **Tests:** [`tests/test_code_task_gate.py`](../../tests/test_code_task_gate.py)
**Doctrine:** NO FAKE GREEN — fail-closed. Generated 2026-07-16.

---

## Why this exists

`backend/agent_executor.py` has long imported a code-verification module under
`if ALLOW_CODE and tclass == "code"`, but the module `scripts/code_task_gate.py` was never
delivered — the imports were dangling. The handoff item `a-codeloop-wire` was marked **SIGNED**
while the artifact it pointed at did not exist. With `AGENT_ALLOW_CODE=1`, the gated path would
raise `ImportError` and fall through to the weaker `_check_acceptance` — i.e. code could run in
code-mode *without* the compile+test gate it is supposed to sit behind. That is a fake-green gap,
and this module closes it.

## What the gate does

For any code-class agent task, the gate is a two-stage, fail-closed verdict:

1. **Compile** — the produced artifact must byte-compile clean (`ast.parse` for a precise
   `SyntaxError`, then `py_compile` as belt-and-suspenders). Non-Python artifacts are reported as
   a skipped-but-ok compile, mirroring the caller's own fallback contract.
2. **Test** — the task's acceptance spec must name a pytest target that **runs and exits 0 with at
   least one test collected**. A code result that ships nothing to prove it works does **not** pass.

`verified` is only ever `True` after a clean compile **AND** a passing pytest run. Every other
branch — missing file, syntax error, missing test target, pytest exit 5 (no tests collected),
failing tests, timeout, or any unexpected exception — resolves to `verified=False`.

## Interface contract (consumed by `agent_executor.py`)

```
compile_check(path) -> (ok: bool, msg: str)
gate(path, spec, cwd=None) -> dict
```

- **`compile_check`** — called in `_verify_compile` (`backend/agent_executor.py` ~L429):
  `ok, msg = compile_check(str(p))`, where `p` is an already-resolved absolute `Path`.
- **`gate`** — called in `execute_task` (`backend/agent_executor.py` ~L620) under
  `if ALLOW_CODE and tclass == "code"`:
  `gate_res = code_gate(fpath, {"tests": spec.get("pytest")}, cwd=str(ROOT))`. The caller reads
  `gate_res["verified"]` (bool) and `gate_res["retry_hint"]` (str). The gate also returns
  diagnostic keys: `compile_ok`, `tests_ok`, `stage`, `detail`, `path`.

The module matches this contract exactly, so the existing imports resolve **without editing the
caller**. If `code_task_gate` is somehow unavailable, `agent_executor` still degrades safely to its
in-file `py_compile` fallback (`_verify_compile`) and `_check_acceptance` — but with the module
present, the real compile+test gate is what runs.

## Failure matrix (fail-closed)

| Condition | Verdict |
|---|---|
| Artifact file missing | `verified=False` (stage: compile) |
| Syntax error / py_compile error | `verified=False` (stage: compile) |
| No pytest target in spec | `verified=False` (stage: tests) — unverifiable ≠ passing |
| pytest exit 5 (no tests collected) | `verified=False` |
| pytest failing tests (exit ≠ 0) | `verified=False` |
| pytest timeout (`CODE_GATE_TEST_TIMEOUT`, default 600s) | `verified=False` |
| Clean compile **and** pytest exit 0 with ≥1 test | `verified=True` |

## Test coverage

`tests/test_code_task_gate.py` — 9 tests, passing (`9 passed` on system python3 / pytest 9.1.1):
clean-pass, syntax-error fail, failing-test fail, missing-test-target fail, no-tests-collected fail,
non-python skip, and fail-closed defaults. Stdlib only — no new dependencies.

## Enablement (founder-gated — do NOT flip casually)

The gate is inert until code mode is on. To enable:

1. Set **`AGENT_ALLOW_CODE=1`** in the process environment.
2. **A fresh process is required.** `ALLOW_CODE` binds at module import in `agent_executor.py`
   (~L42); `_load_env` loads `AGENT_*` into the environment *after* import and does not rebind it,
   so editing `.env` alone will **not** flip an already-running process.
3. For the ag-execution daemon, a fresh process means a **restart** — and per
   [`HOCH_STATUS.md`](../../HOCH_STATUS.md) deploy guardrails, restarting resets the 24h burn-in
   clock. **Do not restart during an active soak/burn-in.** Enable at a clean process launch, after
   the current soak has sealed.
4. Rollback: unset `AGENT_ALLOW_CODE` (or set `0`) and start a fresh process. `DENY_WRITE` continues
   to protect control-plane/secret paths regardless of this flag.

## Doctrine alignment

This closes a real fake-green gap: a SIGNED handoff item whose artifact did not exist. The gate is
delivered, tested, and honest about its own state — present but **disabled**, staged for founder
review. Nothing here enables code mode; that remains a deliberate founder act.
