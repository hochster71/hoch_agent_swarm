# HOCH — Session Handoff (resume point)

*Updated 2026-07-06 (session 2). Read this first in a new session, then `git log --oneline -20` + the docs below.*

## Session 2 progress (commits `d908ac4`..`fbebff7`, on branch goal-ui-v21-runner-release-hygiene-*)
- **Fleet reconciler built** (thread #1): `scripts/hoch_fleet_reconcile.py` — DRY-RUN, resolves each hoch
  launchd plist, follows the entry script one level, statically extracts state-file write-sets, flags
  files written by 2+ jobs as real competing loops, recommends ONE canonical owner per contested class.
  Stops staged as `PENDING_OPERATOR_APPROVAL_T3` (executed=false); no bootout/unload/kill code path.
  Heuristic labeled as such; off-Mac exits honestly (no fabricated fleet). 7/7 tests.
- **Deck panel**: `FLEET RECONCILE` card in `frontend/has_brain_moonshot.html` (live-embed → static mirror
  → NOT-YET-RUN). Reconciler mirrors JSON to `frontend/data/fleet_reconcile.json`. JS syntax-checked.
- **Epic-Fury (thread #2) — RE-GRADED with evidence.** Read the real `~/epic-fury-build` compose files:
  the "2 HIGH Supabase JWTs" are the PUBLIC demo keys (iss=supabase-demo) as env-overridable defaults +
  one public-by-design anon key in a push-*.sh. **No real service_role/privileged credential is leaked.**
  Fixed the root cause: `scan_secrets` now decodes JWT claims (demo/anon→LOW, real service_role→HIGH);
  real-file scan of both build dirs = **0 HIGH, all LOW**. Recurrence guard (version-controlled pre-commit
  hook + installer) still in place. Runbook re-graded to a production *deploy gate* (supply real secrets
  via env before prod — compose already supports it), not an urgent rotation. **No urgent action.**
- Verified in-sandbox only (no launchctl / no browser here). **Pending on the Mac**: run
  `python3 scripts/hoch_fleet_reconcile.py` for the real reconcile plan; render the deck panel live.

## What HOCH is (one Governor, one Mind, many Makers)
- **HOCH** = umbrella. **HAS** = Governor (command & control, evidence discipline). **BRAIN** =
  Mind (multi-domain self-improving gene pools). **Factories** = Makers: **HASF** (software),
  **HMF** (music), **HRF** (research).
- Founding rule, never violated: **no fake-green** — nothing reads green/PASS/SECURE/GO without
  real evidence. $0-first (local Ollama + free tools). T3 (money/publish/deploy/stop-a-runtime)
  needs operator approval.

## What's built + TESTED (committed; latest `b18eefa`)
- **BRAIN acceleration engine**: gap-analysis, gene-expansion (dual-gated), best-of-N, honest
  convergence (blind-flat ≠ converged), research meta-loop. (`backend/brain_convergence/`)
- **3 factories** via `backend/factory/registry.py`; domain scorers for music/research; domain_cycle
  gives HMF/HRF the same expand→select→converge loop + per-factory improvement graphs.
- **AI Michael** founder orchestrator (`backend/orchestrator/founder_orchestrator.py`) — runs the
  decide-loop, autonomous $0 vs escalate-T3.
- **Cyber Swarm** (`backend/swarm/cyber_swarm.py`) — Red seeded faults / Blue real scanners (bandit +
  secret-detector) / Purple convergence; 100% detection coverage; secret patterns built from
  ordinals so the repo stays clean.
- **Self-heal** (`backend/swarm/self_heal.py`) — scans HOCH source for secrets, quarantines/escalates,
  installs a recurrence guard (`tests/integration/test_no_literal_secrets.py`), seeded-fault proven.
- **NIST 800-53 Rev 5 arterial map** (`backend/swarm/nist_map.py`) — 18/20 families covered, 917
  gene→control paths; brain-hover on the deck.
- **HASF Product Gate Verifier** (`scripts/hasf_product_gate_verify.py`) — fail-closed; caught the
  old Epic-fury APPROVED as NO-GO.
- **Fleet audit** (`scripts/hoch_fleet_audit.py`) — enumerates all launchd runtimes (proven live).
- **Command deck** (`frontend/has_brain_moonshot.html`) — living BRAIN core, factory cockpit cards,
  swarm agents (spin + hover), NIST brain-hover, chat dock, STALE-proof (static fallback).
- 22 integration tests pass. Console JS syntax-checked (not browser-rendered by the agent).

## What's RUNNING
- Continuous daemon `com.hoch.daemon` (10s loop: brain + factories + swarm + self-heal + AI Michael
  + audits + publish). Backend `com.hoch.agent.swarm.runtime`. Deck at
  `https://michaels-macbook-pro.tail826763.ts.net/has_brain_moonshot.html` (Tailscale-private).
- **Fleet = ~45 hoch runtimes** (21 running). See "open threads" — there are competing loops.

## OPEN THREADS / next moves
1. **Fleet reconciliation (highest leverage).** Dry-run reconciler is now BUILT (session 2). NEXT:
   run `python3 scripts/hoch_fleet_reconcile.py` on the Mac to produce the real
   `data/prompt_brain/fleet_reconcile.json`, review the per-class canonical-owner recommendations, then
   **operator-approve each T3 `launchctl bootout`** one at a time (nothing is stopped automatically).
   After that, wire the reconcile output into the live BRAIN feed so the deck panel shows it in real time.
2. **Epic-fury (first monetized app) — DOWNGRADED from blocker (session 2, evidence-based).** The
   flagged JWTs are public Supabase demo defaults + a public anon key; **0 real HIGH** after decoding
   (verified against the real files with the fixed scanner). No urgent action. Remaining item is a
   pre-production *deploy gate*: inject real Supabase secrets via env before a prod deploy (compose
   already reads `${VAR:-demo-default}`), per `docs/runbooks/epic-fury-secret-rotation.md`. T3, operator.
3. **HMF/HRF real gains** need frontier judges (audio-quality, research-novelty) = cost/Rung-2 —
   deferred. Their mechanical proxy is near ceiling (93/96); graphs may sit flat honestly.
4. **HFP** (Hoch Family/Personal Factory) — note: `com.hoch.family.*` already runs as a live fleet.
5. **Control-plane visual** — the dark AI-generated hover-live control plane is the culmination once
   wiring is reconciled.

## How to resume
`git log --oneline -20`; read `docs/architecture/HOCH_FACTORY_ARCHITECTURE.md`,
`docs/architecture/AI_MICHAEL_FOUNDER_ORCHESTRATOR.md`, `docs/pert/HOCH_GAP_ANALYSIS.md`, and this
file. Run `python3 scripts/hoch_fleet_audit.py` and `python3 -m backend.orchestrator.agent_audit`
to see live state.
