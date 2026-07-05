# Git Hygiene Plan — reaching the "clean git status" baseline gate

* **Status**: PROPOSAL for operator review. No bulk change applied by the agent.
* **Captured (UTC)**: 2026-07-05
* **Why**: Readiness carries a 90-cap for "git working tree is dirty". The tree shows
  ~245 changes (136 untracked, 101 modified, 8 deleted). Most are runtime-generated
  state files the running system rewrites every cycle, so the tree cannot go clean while
  HAS runs unless that state is untracked. The remaining changes are real source/test
  work that should be reviewed and committed deliberately — not swept in with `git add -A`.

---

## 1. Root cause

`.gitignore` ignores *some* runtime state (`events.ndjson`, `scheduler_metrics.json`,
`usage_metrics.json`, …) but not the bulk of machine-written JSON under
`has_live_project_tracker/data/`, `data/prompt_brain/`, and generated `dist/releases/` and
`docs/evidence/` artifacts. Those churn on every cycle → perpetual dirty tree → the
"clean git status" / baseline-closure gate can never pass.

**Fix shape:** stop tracking machine-written state, then the only remaining diff is
human-authored source, which can be committed to reach a clean tree.

---

## 2. Bucket A — runtime state to STOP tracking (churns every cycle)

Review each glob; these are machine-written, not source. Add to `.gitignore`, then remove
from the index (keeps the files on disk, only stops tracking):

```gitignore
# --- runtime-generated state (machine-written; do not track) ---
has_live_project_tracker/data/*.json
data/prompt_brain/*.jsonl
data/prompt_brain/**/*.jsonl
data/prompt_brain/live_runtime_summary.json
data/prompt_brain/model_adapter_status.json
data/prompt_brain/model_performance_matrix.json
```

```bash
# stop tracking already-committed state files (files stay on disk)
git rm -r --cached --quiet \
  has_live_project_tracker/data \
  data/prompt_brain 2>/dev/null || true
# NOTE: keep any *fixture* files you rely on for tests — re-add them explicitly:
#   git add -f has_live_project_tracker/data/<fixture>.json
```

CAUTION before running: confirm nothing under these paths is a versioned fixture a test
loads. Grep first:

```bash
grep -rIl "has_live_project_tracker/data/" tests/ | sort -u
```

Anything a test reads should be force-re-added (`git add -f <path>`) or moved to a
`fixtures/` dir that is not ignored.

---

## 3. Bucket B — real SOURCE / TEST work to REVIEW and commit

These are human-authored and belong in git. Review diffs, then commit in logical groups.

New tests (high value — commit first):
```
tests/test_seeded_faults.py
tests/test_quarantine_guards.py
scripts/verify_*.py   (verify_daemon_heartbeat, verify_ag_execution_*, verify_has_prr_criteria, …)
scripts/ag_execution_daemon.py, ag_execution_failure_injector.py, ag_execution_supervision_test.py
```

Modified source (review each diff before staging):
```
backend/model_router/google_frontier.py, router.py
backend/runtime_truth/collector.py, contradiction_detector.py, state_store.py
backend/final_verifier/readiness_cap_engine.py
scripts/ag_execution_*, has_autonomous_cadence.py, refresh_heartbeats.py, rc*_verify.sh
infra/hoch-200/vps/{relay-api/app.py,docker-compose.yml,dashboard/index.html}
tools/has_live_truth_sidecar.py
frontend/index.html
tests/e2e/*.spec.ts, tests/test_model_router_policy.py, tests/test_staging.py
```

Suggested grouping:
```bash
# 1) tests + verifiers
git add tests/test_seeded_faults.py tests/test_quarantine_guards.py scripts/verify_*.py \
        scripts/ag_execution_daemon.py scripts/ag_execution_failure_injector.py \
        scripts/ag_execution_supervision_test.py
git commit -m "test: add seeded-fault, quarantine, and verifier suites"

# 2) runtime-truth + model-router source (review diffs first!)
git add backend/runtime_truth/*.py backend/model_router/*.py backend/final_verifier/readiness_cap_engine.py
git commit -m "chore(backend): sync runtime-truth + model-router source"
```

---

## 4. Bucket C — deletions to reconcile

An apparent migration removed the legacy standalone tracker app. Confirm intentional,
then stage the deletions:
```
frontend/archive/unused_views.html, unused_views.js
has_live_project_tracker/app.js, index.html, index_backup.html, server.js,
  server_backup.js, tracker-mirror.html
```
```bash
git add -A frontend/archive has_live_project_tracker/*.html has_live_project_tracker/*.js
git commit -m "chore: remove legacy standalone tracker app (migrated into main frontend)"
```

---

## 5. Order of operations to reach a clean tree

1. Bucket B commits (source/tests) — the real work, reviewed.
2. Bucket C commit (deletions) — confirm intentional.
3. Bucket A `.gitignore` + `git rm --cached` — stop the churn (do LAST so you can still
   diff state if needed).
4. Re-run: `git status --short | wc -l` should approach 0, and
   `.venv/bin/python -c "from backend.final_verifier.final_verdict import FinalVerdict; print(FinalVerdict().get_final_verdict()['readiness_caps'])"`
   should drop the "git working tree is dirty" cap.

Each step is reversible; nothing here deletes source or moves tags. The release GO cap is
separate and remains an operator release decision.
