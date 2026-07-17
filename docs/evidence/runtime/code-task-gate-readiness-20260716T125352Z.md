# Code-Task Gate — Readiness & Founder Enable Procedure

Generated: 2026-07-16T12:53:52Z (UTC)
Author: HELM subagent (read-only investigation). Doctrine: NO FAKE GREEN — every claim below
cites an exact file + line. Where I could not confirm, it says UNKNOWN.
Scope: DOC ONLY. I did NOT set AGENT_ALLOW_CODE, did NOT edit code, did NOT touch the daemon,
ledgers, or runtime files. Enabling the gate is a FOUNDER-GATED action (see §C).

---

## TL;DR

The gate *call sites* are present in `backend/agent_executor.py`, but the module they import —
`scripts/code_task_gate.py` — **DOES NOT EXIST** anywhere in the repo. The signed handoff item
`a-codeloop-wire` names that exact file as its `blocking_evidence`, and it is missing. So the
"Wire code_task_gate" work is **NOT truly delivered**: with `AGENT_ALLOW_CODE=1`, code tasks
would hit an `ImportError` and silently fall back to the weaker `_check_acceptance` path — i.e.
code would run in code-mode *without* the compile+test gate it is supposed to be fenced behind.
This is a FAKE-GREEN gap: SIGNED in the queue, absent on disk.

---

## A. Current State — is the gate truly wired in?

### A.1 What EXISTS (verified)

- Env flag read (module-level, bound ONCE at import):
  `backend/agent_executor.py:42` — `ALLOW_CODE = os.environ.get("AGENT_ALLOW_CODE") == "1"`
  Header comment `:41` — "Set AGENT_ALLOW_CODE=1 to enable guarded code edits + shell."

- Safe-mode enforcement that the flag controls:
  - `backend/agent_executor.py:207-208` — `_write_file`: without ALLOW_CODE, writes are limited
    to `WRITE_ROOTS = ("docs/", "scratch/", "artifacts/")` (`:37`).
  - `backend/agent_executor.py:218-219` — `_run_command`: returns "run_command disabled in safe
    mode" unless ALLOW_CODE.
  - `backend/agent_executor.py:485-486` — acceptance: pytest step is SKIPPED (safe mode) unless
    ALLOW_CODE.

- Gate call sites that import the (missing) module:
  - `backend/agent_executor.py:429` — inside `_verify_compile`:
    `from scripts.code_task_gate import compile_check` → `compile_check(str(p))`.
    Has a fallback (`:431-440`): on any Exception it runs `python -m py_compile` directly.
  - `backend/agent_executor.py:617-643` — the main wiring, guarded by
    `if ALLOW_CODE and tclass == "code":` (`:618`):
    `from scripts.code_task_gate import gate as code_gate` (`:620`), then for each acceptance
    file calls `code_gate(fpath, {"tests": spec.get("pytest")}, cwd=str(ROOT))` (`:632`),
    accepts on `gate_res.get("verified")`, else re-tries with `gate_res.get("retry_hint")`
    (`:636-637`). On Exception it falls back to `_check_acceptance` and appends
    `"code gate error: {e}"` (`:641-643`).

- Escalation/retry loop that consumes the gate result: `backend/agent_executor.py:612-660`
  (attempt loop, one tier up per retry, `MAX_RETRIES` `:420`).

### A.2 What is MISSING (verified — this is the gap)

- `scripts/code_task_gate.py` **does not exist.** `find . -name "code_task_gate*"` returns
  nothing; the only references in the codebase are the two imports at
  `backend/agent_executor.py:429` and `:620`. No `def gate(` or `def compile_check(` exists in
  any module under a `code_task_gate` name (searched repo-wide).
- Referenced design doc `docs/factories/CODE_LOOP_RELIABILITY.md` (named in the handoff `action`)
  **does not exist** either.

### A.3 The signed-vs-delivered mismatch (FAKE-GREEN flag)

`has_live_project_tracker/data/founder_handoff_queue.json`, item `a-codeloop-wire`:
- `title`: "Wire code_task_gate into agent_executor (change board)"
- `gate`: "blocked_release"
- `blocking_evidence`: `scripts/code_task_gate.py`  ← the file that is MISSING
- `status`: "SIGNED", `signed_by`: "Michael Bryan Hoch", `signed_at`: 2026-07-09T08:35:00Z
- `action`: "...call scripts/code_task_gate.gate(file,acceptance); accept on verified, else retry
  with retry_hint (cap N). Behind AGENT_ALLOW_CODE=1. ... See docs/factories/CODE_LOOP_RELIABILITY.md."

Verdict: the call sites match the signed intent, but the delivered artifact (`code_task_gate.py`)
and its design doc are absent. The item is SIGNED yet the evidence file it points to is not on
disk. **The gate is NOT truly wired** — it is a dangling import guarded by try/except that
degrades to the non-gate path.

### A.4 Behavioral consequence (verified from the fallbacks)

- `_verify_compile` (`:429`) degrades gracefully to `py_compile` — acceptable for compile.
- The main code path (`:618-643`), however, on ImportError does NOT compile+test via the gate;
  it falls to `_check_acceptance` (`:641`). Net effect if AGENT_ALLOW_CODE=1 today: code tasks
  execute with write+shell powers but WITHOUT the compile+tests+retry_hint gate they are supposed
  to be fenced behind. That is the opposite of the intended safety posture.

---

## B. What flipping AGENT_ALLOW_CODE=1 would do

Because `ALLOW_CODE` is read at `backend/agent_executor.py:42`, setting the env var to `1`
switches these behaviors for the agent executor (and, separately, `scripts/northstar_daemon.py:30`
reads the same var):

1. **Opens the develop/write lane** — `_write_file` (`:207-208`) no longer restricts writes to
   `docs/ scratch/ artifacts/`; the agent may write source files. Still hard-blocked:
   the `DENY_WRITE` set (`:47-54`) — `baseline_guard.py`, `ag_execution_daemon.py`,
   `ag_execution_runner.py`, `agent_executor.py`, the northstar planner/daemon, `model_upgrade.py`,
   the orchestration-bridge control JSON, `baseline_tag.txt`, `ag_execution_policy.json`,
   `.env`, `.git/`, `.secrets/`, `config/`, `.gitignore`. Those remain refused even in code mode.
2. **Enables guarded shell** — `_run_command` (`:218-219`) turns on, limited to the read-only/
   test/lint allowlist `_CMD_ALLOW` (`:57-58`), python only as `-m py_compile`/`-m pytest`
   (`:225-227`), git read-only subcommands only (`:228-230`), no chaining/redirect/subshell
   (`:221-222`).
3. **Turns on the pytest acceptance step** — `_check_acceptance` (`:485-489`).
4. **Activates the code-gate branch** at `:618` (`if ALLOW_CODE and tclass == "code":`) — which,
   given §A.2, currently throws ImportError and falls back (see §A.4). So flipping the flag today
   does NOT give you the intended gate; it gives you code-mode minus the gate.

Which develop lanes it closes: the factories' `next_action` is uniformly "close develop lane
behind code-task gate" + "founder: enable AGENT_ALLOW_CODE". Closing the develop lane *behind the
gate* is only real once `code_task_gate.py` exists (§A.2). The exact per-factory lane list was not
enumerated in this pass — UNKNOWN (not verified here); the mechanism, not the roster, is the
blocker.

---

## C. Safe, ordered founder procedure to enable it

> This is a FOUNDER GATE. I did NOT enable anything. Do not run any of the steps below on my behalf
> without the founder performing/authorizing them. A live 24h Phase C soak is running — see the
> restart caveat in C.4, it is the critical risk.

**C.0 — Do NOT enable yet.** Recommended: first CLOSE the real gap (author
`scripts/code_task_gate.py` exporting `gate(file, acceptance, cwd)` → `{verified, retry_hint}` and
`compile_check(path)` → `(ok, msg)`, plus `docs/factories/CODE_LOOP_RELIABILITY.md`). That is a
code change on the change board (edits are gated by baseline_guard + founder commit per the handoff
item) and is out of scope for this doc. Enabling the flag before that yields code-mode-without-gate
(§A.4).

**C.1 — Env location.** There is NO env wiring for this var today (verified):
- `deploy/local-autonomy/com.hoch.ag.execution-daemon.plist` has NO `EnvironmentVariables` key
  (only ProgramArguments/WorkingDirectory/KeepAlive/log paths).
- No `.env` / plist / shell sets `AGENT_ALLOW_CODE` anywhere in the repo (grep returned only the
  two *read* sites in `agent_executor.py:42` and `northstar_daemon.py:30`).
So to turn it on for the daemon-run executor, the founder must put it in the daemon's process
environment. Two candidate locations:
  (a) Add `<key>EnvironmentVariables</key><dict><key>AGENT_ALLOW_CODE</key><string>1</string></dict>`
      to `com.hoch.ag.execution-daemon.plist`, or
  (b) Add `AGENT_ALLOW_CODE=1` to `/Users/michaelhoch/hoch_agent_swarm/.env`.

**C.2 — .env caveat (important).** `_load_env` (`:263-278`) DOES import any `AGENT_*` key from
`.env` into `os.environ` (`:277` — `k.startswith("AGENT_")`). BUT `ALLOW_CODE` is bound at module
IMPORT time (`:42`), whereas `_load_env()` runs later, inside `_gateway_generate` (`:312`), and it
never rebinds the module-level `ALLOW_CODE`. Therefore putting it in `.env` will NOT flip the
already-imported `ALLOW_CODE` in a running process — the value is fixed for that process's life.
The flag only takes effect if it is present in the process env at IMPORT/launch time.

**C.3 — Because of C.2, a fresh process is required.** For a one-shot / manual executor run,
launch with the var exported (`AGENT_ALLOW_CODE=1 .venv/bin/python3 ...`). For the daemon, the
value must be in its launch environment (plist EnvironmentVariables) AND the daemon must start a
new process to pick it up.

**C.4 — Restart guardrail (the hard constraint).** `HOCH_STATUS.md:38-43` — "DEPLOY GUARDRAILS":
"NEVER restart hoch-ag-execution-daemon.service to pick up config/runner changes. ... Restarting
the daemon resets started_at + the 24h burn-in clock to zero (cost us a 33h run on 2026-07-07).
Only restart when ag_execution_daemon.py ITSELF changes." Config/policy/runner JSONs re-read every
cycle WITHOUT a restart — but `AGENT_ALLOW_CODE` is NOT one of those; it is a module-import-time
env read (§C.2), so it CANNOT propagate mid-run. This is the core tension: enabling code mode on
the daemon requires a new process, which resets the burn-in clock. Do NOT do this during the live
soak. Sequence it for AFTER the current 24h Phase C soak completes (do not disturb the running
soak).

**C.5 — Ordered enable (post-soak, after C.0 gap is closed):**
  1. Land `scripts/code_task_gate.py` + `docs/factories/CODE_LOOP_RELIABILITY.md` via the change
     board (baseline_guard + founder commit).
  2. Confirm imports resolve: `python -c "from scripts.code_task_gate import gate, compile_check"`.
  3. Add `AGENT_ALLOW_CODE=1` to the daemon launch env (plist EnvironmentVariables, C.1a).
  4. Wait for the live burn-in run to finish (respect HOCH_STATUS.md:38-43); only then reload the
     LaunchAgent so a fresh process reads the flag.
  5. Verify from a code task that the gate branch (`:618`) runs and `code_gate` returns
     `verified/retry_hint` (not the ImportError fallback at `:641`).

---

## D. Rollback

- **Fastest:** remove/unset `AGENT_ALLOW_CODE` (delete the plist EnvironmentVariables entry or the
  `.env` line) and start a fresh executor/daemon process. On next import, `:42` evaluates to
  `False` → executor returns to safe file-only mode (`_write_file` limited to WRITE_ROOTS,
  `_run_command` disabled, pytest skipped). Same restart caveat (C.4) applies to the daemon.
- **Belt-and-suspenders:** `DENY_WRITE` (`:47-54`) protects the control plane / secrets / guard /
  daemon / runner even while code mode is on, so a rollback never has to worry about the agent
  having edited those.
- **No data migration / no schema change** is involved; the flag is purely behavioral, so rollback
  is just un-setting the env var and cycling a fresh process.

---

## E. Evidence index (files + lines cited)

- `backend/agent_executor.py` — :37, :41-43, :47-58, :207-208, :218-230, :263-278, :312, :429-440,
  :485-489, :612-660, :617-643
- `scripts/northstar_daemon.py:30` — same env read
- `scripts/code_task_gate.py` — **MISSING** (imported at agent_executor.py:429,:620)
- `docs/factories/CODE_LOOP_RELIABILITY.md` — **MISSING** (referenced by handoff action)
- `has_live_project_tracker/data/founder_handoff_queue.json` — item `a-codeloop-wire` (SIGNED,
  blocking_evidence = the missing file)
- `deploy/local-autonomy/com.hoch.ag.execution-daemon.plist` — no EnvironmentVariables key
- `HOCH_STATUS.md:38-43` — deploy guardrails (do-not-restart daemon / burn-in clock reset)

Enablement NOT performed. This document is advisory only.
