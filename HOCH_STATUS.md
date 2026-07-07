# HOCH SYSTEM STATUS — Machine-readable session-start artifact
# Updated: 2026-07-07 | Read this FIRST before any session work.
# Purpose: eliminates re-diagnosis overhead. Every session starts here, ends with an update.

## BRAIN (HASF)
- generation: 712 | mean: 94.417 | state: CONVERGED
- live_model: lmstudio (gemma-4-12b-qat) PRIMARY — 4/4 backends alive
- gateway backends: lmstudio → mac-local → mac-tailscale → relay-001
- champion_executions: 8 (ledgered) | genes_with_combat_record: 1 (Incident Response)
- fitness: BLENDED_CONFIDENT wired — outcome-based scoring active
- HMF: gen 663 mean 96.9 CONVERGED (frozen — expand pool or harden rubric to unblock)
- HRF: gen 662 mean 96.5 CONVERGED (same)

## MODEL GATEWAY (backend/model_gateway.py) ✅ LIVE
- lmstudio 127.0.0.1:1234 — gemma-4-12b-qat + nemotron-3-nano — OpenAI API
- mac-local 127.0.0.1:11434 — llama3.1:8b (GOOD store: ~/.ollama/models)
- mac-tailscale 100.103.155.4:11434 — same store, LaunchAgent managed
- relay-001 100.87.18.15:11434 — qwen2.5:1.5b — 24/7 Docker, always-on backstop
- MODEL_OFFLINE structurally eliminated — any backend alive = service up

## LIVE-REAL-ONLY — WHAT WAS REMOVED (do not re-add)
- SimulationFallbackAdapter: DISABLED (was injecting fake evidence hashes)
- generate_premium_fallback: DELETED (was returning fabricated research reports)
- fake confidence score (95/92 by keyword): REMOVED → null
- Orchestrator failure-laundering (failed→passed auto-repair): REMOVED
- random-walk CPU/RAM fleet vitals: REMOVED
- canned activity strings (Self-Healing/Triaging theater): REMOVED
- /prototype/prompt-brain: 410 RETIRED (2763 lines of hardcoded demo HTML)
- outreach/pilot fabricated data: QUARANTINED → data/prompt_brain/_quarantine_fabricated_20260706/

## LAUNCHAGENTS (all managed, survive reboot)
- com.hoch.api.server — uvicorn backend.main:app :8000 KeepAlive
- com.hoch.brain.cadence — brain_cadence.sh every 600s
- com.hoch.ollama.tailscale — Ollama on 100.103.155.4:11434 (good store)
- com.hoch.daemon — hoch_cadence.sh master orchestrator
- com.hoch.goal.runtime.loop — goal runtime

## DEPLOY GUARDRAILS (learned the hard way)
- ⛔ NEVER restart hoch-ag-execution-daemon.service to pick up config/runner changes.
  The runner (scripts/ag_execution_runner.py) and its policy/config JSONs are re-read
  EVERY cycle, so DOORSTEP-posture / policy / runner edits propagate WITHOUT a restart.
  Restarting the daemon resets started_at + the 24h burn-in clock to zero (cost us a 33h
  run on 2026-07-07). Only restart when ag_execution_daemon.py ITSELF changes.
- Burn-in ledger is append-only across runs; cycle_ids are run-namespaced (run-<UTC>-cycle-NNNNN)
  so restarts never overwrite prior evidence — the counter resets, the proof does not.
- ⛔ NEVER run scripts/secure_sync_hoch200.sh as a "pull truth" step. It rsyncs LOCAL→REMOTE
  and does not exclude has_live_project_tracker/data — it will clobber live relay runtime
  state with stale local copies. Pull the relay's copy over SSH/HTTP instead.
- Relay config/runner deploys: scp the specific files, do NOT full-sync. Relay ollama is a
  container → pull models via `docker exec ollama ollama pull <tag>`, not host `ollama`.

## FLEET (8/9 reachable)
- L1 (Mac): MEASURED_LOCAL — cpu/ram/agents from psutil+launchctl
- L2,L3,W1,iPads: UNREACHABLE (powered off) — declared config, not measured
- iPhone: DECLARED_ROSTER_NOT_MEASURED (reachable, no telemetry agent)
- HOCH-200 relay: ONLINE 24/7 (Tailscale 100.87.18.15)

## LEDGERS (append-only, never modify)
- data/prompt_brain/runtime_usage_ledger.jsonl — every champion/fallback use
- data/prompt_brain/outcome_feedback_ledger.jsonl — gate results + execution outcomes

## EPIC FURY 2026 — iOS Store Review
- Status: FOUNDER REVIEW IN PROGRESS (2026-07-07)
- Local: http://localhost:3003 (next dev, pid 44918)
- Vercel: https://epic-fury-2026.vercel.app
- Gate verdict: NO-GO (HASF_GATE_VERIFY.json) — 18 HIGH open, security scan used fallbacks
- Build: ✅ SUCCESS | TypeScript: ✅ CLEAN | npm audit: 0 vulnerabilities
- Smoke tests: ✅ PASS | Mobile layout: ✅ PASS
- BLOCKING for App Store: Stripe live keys not configured, security scan needs real binaries
- iOS bundle: com.epicfury.dashboard | Capacitor + RevenueCat/IAP

## NEXT ORDERED TASKS (pick top, do not skip)
1. [EPIC-FURY] Founder human review → feedback → final gate → App Store push
2. [BRAIN] Wire real gate outcomes into HMF/HRF fitness (currently rubric-only, no combat records)
3. [BRAIN] First real mission with task_class through champion → ledger → outcome chain at scale
4. [OUTREACH] Replace quarantined fake pipeline with real buyer contacts (founder action)
5. [FLEET] Telemetry agents on HOCH-200 relay (real agent counts from remote node)

## WHAT DOES NOT NEED DIAGNOSIS (already solved)
- Ollama split-brain: FIXED (bad store on Tailscale daemon → repointed to ~/.ollama/models)
- Dead-model fake liveness: FIXED (generation probe mandatory, not tags listing)
- Champion loader: LIVE (backend/factory/champion_loader.py + runtime_ledger.py)
- Blended fitness: LIVE (backend/brain_convergence/scorer.py blended_score())
- Fleet theater: REMOVED (honest telemetry only)
- Fake green audit: COMPLETE for major offenders (sweep report: docs/evidence/fake_green_sweep_*.txt)

## DASHBOARD URLS
- Command Deck: http://127.0.0.1:8000/has_brain_moonshot.html
- Tailscale: http://michaels-macbook-pro.tail826763.ts.net:8000/has_brain_moonshot.html
- Live feed: http://127.0.0.1:8000/api/brain/live
- Gateway status: http://127.0.0.1:8000/api/gateway/status
- Epic Fury local: http://localhost:3003
