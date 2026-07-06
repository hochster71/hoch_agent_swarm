# HOCH — Session Handoff (resume point)

*Written 2026-07-06. Read this first in a new session, then `git log --oneline -20` + the docs below.*

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
1. **Fleet reconciliation (highest leverage).** 3 classes have competing loops: SWARM
   (`live-swarm`, `phase72a.cyber.rag`, new `cyber_swarm`), EXECUTOR/CADENCE (`autonomous.executor`,
   `phase73b.factory.tick`, new `daemon`), AUDIT (`hochmesh.autonomous-audit`, new `agent_audit`).
   Next build = **dry-run reconciler** (detect same-file writers, recommend one canonical owner per
   class, change nothing until operator approves each stop). Stopping a runtime is T3.
2. **Epic-fury (first monetized app) — REAL blocker:** 2 HIGH hardcoded Supabase JWT tokens in
   `~/epic-fury-build/epic-fury-2026/docker-compose.yml` + `docker-compose.dev.yml`. Self-heal
   correctly can't un-leak them — **operator must rotate** before ship.
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
