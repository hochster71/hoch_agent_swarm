# HELM BASELINE TRACEABILITY MATRIX — Phase 0 (pre-build audit)

- **Author:** HELM baseline-audit agent (READ-ONLY pass)
- **Generated:** 2026-07-17T13:20:20Z
- **Repo:** `/Users/michaelhoch/hoch_agent_swarm`
- **Purpose:** Before building HELM Voice executive interface + HELM Cyber Command Center, establish an HONEST inventory of what already exists in-repo vs. what is only claimed. Grok audit returned 51/100 NOT READY — this matrix says what that score is actually sitting on.
- **NO FAKE GREEN:** classifications reflect on-disk evidence only. The live API (port 8770) runs on Michael's Mac and is **NOT reachable from this Linux workspace mount**, so nothing here is marked VERIFIED_LIVE from a live curl this run. Where log evidence proves it served 200 recently, that is called out explicitly.

## Classification legend
VERIFIED_LIVE · IMPLEMENTED_UNVERIFIED · PARTIAL · MOCKED · PLANNED · STALE · BROKEN · ABSENT · UNKNOWN

---

## 1. VOICE

| Component | Class | Evidence |
|---|---|---|
| Voice routes `/api/v1/helm/voice/*` | **IMPLEMENTED_UNVERIFIED** (live-recent) | `backend/voice/router.py` — `APIRouter(prefix="/api/v1/helm/voice")` with `/policy`, `/policy/reload`, `/commands`, `/brief`, `/command` (POST+GET), `/sanitize`, `/tools`, `/health`, `/mission`. Included in `backend/helm_live_api.py:114-115`. Log `logs/helm_live_voice.out.log` shows `GET /api/v1/helm/voice/health 200 OK` and `GET /voice 200 OK` — **but log mtime is 2026-07-15** (2 days old) and the API is not up in this workspace. So: code real, served 200 recently, not verifiable right now. |
| `voice.html` + `voice_panel.js` | **IMPLEMENTED_UNVERIFIED** | `frontend_live/voice.html` (175 lines), `frontend_live/voice_panel.js` (428 lines). Served by `helm_live_api.py:1583` (`/voice`) and `:1602` (`/frontend_live/voice_panel.js`). Present, non-trivial, served 200 in the 07-15 log. |
| ElevenLabs integration (`backend/voice/*`) | **PARTIAL / gated-OFF** | `backend/voice/elevenlabs_tts.py` implements the provider + `elevenlabs_config_status()`. **Fail-closed and disabled by default**: `policy.py` `elevenlabs_enabled: False`, requires `ELEVENLABS_API_KEY` + `paid_providers_allowed`/`HELM_VOICE_PAID_PROVIDERS` + explicit enable. Default `voice_mode: local_tts`. Code is real; premium path is OFF until Michael sets key+paid flag. Not a mock — a deliberately-gated real integration. |
| Executive / mission voice endpoints | **IMPLEMENTED_UNVERIFIED** | `router.py:/mission` and `/brief` call the SAME Mission State Engine (`backend.mission_control.mission_state.write_mission_state`) and `build_executive_brief()`. `execute_voice_command` in `backend/voice/briefing.py` (45KB). Governed read-only/stage-only by design. Cost gate wired (`cost_gate.py`, `config/voice_policy.yaml`). |
| Voice command governance surface | **IMPLEMENTED_UNVERIFIED** | `commands.py`, `policy.py`, `sanitizer.py`, `tools_schema.py` (Grok tool schema), `security_events.py`, `role_agents.py`, `factory_agents.py`, `extended_factories.py`. Config: `config/voice_policy.yaml`, `config/voice_agent_tools.json`. Tests exist: `tests/unit/test_helm_voice_executive.py`, `tests/unit/test_voice_cost_gate.py`, `tests/e2e/rc54-voice-sidecar-policy.spec.ts`. Extensive design docs under `docs/architecture/HELM_VOICE_*` and `docs/evidence/runtime/voice-*`. |

**Voice bottom line:** the voice interface is **substantially already built** (routes, UI, governance, cost gate, ElevenLabs provider, tests, design docs) — NOT a greenfield. What's missing is a *live current-run verification* and the ElevenLabs premium path being switched on. Build should be "verify + finish + turn on," not "build from scratch."

---

## 2. MISSION STATE

| Component | Class | Evidence |
|---|---|---|
| Canonical mission-state engine | **IMPLEMENTED_UNVERIFIED (fresh output)** | Engine is `backend/mission_control/mission_state.py` (NOT `coordination/goal/mission_state.py` — that path is the JSON *output*, not code). Exposes `write_mission_state()` + `render_executive_text()`. |
| `/api/v1/helm/mission*` endpoints | **IMPLEMENTED_UNVERIFIED** | `helm_live_api.py:687-728` serves `/api/v1/helm/mission`, `/mission/state`, `/mission/executive`. Also `/mission` HTML dashboard (`:1594`, needs `frontend_live/mission.html`). Voice router `/mission` shares the same engine (single source of truth — good). |
| Output freshness | **FRESH** | `coordination/goal/mission_state.json` `computed_at: 2026-07-17T13:09:15Z` (~10 min old at audit). Writer is live and recent. |
| Who writes / reads | Writer: `write_mission_state()` (engine) → `coordination/goal/mission_state.json`. Readers: helm_live_api mission endpoints, voice router `/mission` + `/brief`, mission.html dashboard. Single canonical engine, multiple readers — clean. |

**Mission-state bottom line:** real, single-source, freshly computed. Safe to build on.

---

## 3. RUNTIME TRUTH ENDPOINTS (`backend/truth/*`)

All truth endpoints are **IMPLEMENTED_UNVERIFIED this run** (API not reachable from the mount), but each is fail-closed, reads real on-disk evidence, and carries a freshness/`_truth_response` contract. Backing evidence freshness assessed directly:

| Endpoint | Class | Backing source + freshness |
|---|---|---|
| `/api/v1/helm/goal` | **IMPLEMENTED_UNVERIFIED** | `coordination/goal/goal_state.json` computed **2026-07-17T13:09:15Z (fresh)**. ⚠️ Critical-path requirements show `state: FAILED` with detail **"No module named pytest"** — the fail-closed validators cannot execute in the Xcode python, so weighted goal% is being dragged down by tooling breakage, not just real gaps. Also REQ-CP-APP_STORE_CONNECT FAILED (ASC key not set). This is the honest core of the 51/100. |
| `/api/v1/helm/factories` | **IMPLEMENTED_UNVERIFIED** | `backend/truth/integrity.py::canonical_factories()` reads `coordination/council/factory_registry.json` — **exists, fresh (Jul 17 08:19)**. |
| `/api/v1/helm/runtime` | **IMPLEMENTED_UNVERIFIED** | `backend/truth/runtime_source.py::concurrency_truth`; POINTER `coordination/council/active_runtime_source.json` — **exists, fresh (Jul 17 08:19)**. |
| `/api/v1/helm/wall` | **IMPLEMENTED_UNVERIFIED (live-recent)** | `backend/truth/wall_state.py`. Log shows `GET /api/v1/helm/wall 200 OK` on 07-15. Every scope derived independently. |
| `/api/v1/helm/agents` | **IMPLEMENTED_UNVERIFIED** | Reads newest soak package daemon ledgers (`result_envelopes.jsonl`, `verification_ledger.jsonl`). 27 `HELM-SOAK-*` packages exist; newest `HELM-SOAK-24H-20260716T201324Z`. Fail-closed → UNKNOWN if no package. |
| `/api/v1/helm/chain` | **IMPLEMENTED_UNVERIFIED** | `backend/truth/evidence_chain.py::verify_chain` (AU-9). Reads `task_lease_ledger.jsonl`; returns `CONTRADICTED` on break. Honest by construction. |
| `/api/v1/helm/tasks` | **IMPLEMENTED_UNVERIFIED** | `backend/swarm_ledger.db` — **fresh (Jul 17 07:57)**. |
| `/api/v1/helm/integrity` | **IMPLEMENTED_UNVERIFIED** | `backend/truth/integrity.py::compute_integrity` over live tasks. |
| `/api/v1/helm/pert` | **IMPLEMENTED_UNVERIFIED** | `_api_v1_pert_body()` multi-source aggregation; explicitly fail-soft to `state: UNKNOWN` rather than 500. |

Other truth files present: `authority_binding.py`, `runtime_source.py`, `soak_select.py`, `supply_chain.py`, `task_status.py`, `wall_state.py`, plus a parallel `backend/runtime_truth/` package (freshness, claim_guard, contradiction_detector, readiness_calculator, go_nogo_manager, etc.).

**Runtime-truth bottom line:** the truth layer is mature, fail-closed, and well-architected — a genuine asset. The one red flag is the **pytest-missing validator breakage** poisoning goal-state, which looks like environment rot, not a design gap.

---

## 4. SECURITY POSTURE SURFACES (NIST / RMF / zero-trust / conmon / STIG / SBOM / CVE)

| Component | Class | Evidence |
|---|---|---|
| NIST CSF 2.0 × 800-53 control matrix | **IMPLEMENTED_UNVERIFIED** | `backend/helm/nist_matrix.py` (551 lines) — executable assessors (COVERED/PARTIAL/UNVERIFIED, fail-closed). Wired: `nist_router` at `/api/v1/helm/nist` + `/nist` HTML, included in `helm_live_api.py:110-111`. This is the strongest existing seed for the Cyber Command Center. |
| Control catalog | **IMPLEMENTED_UNVERIFIED** | `backend/security/helm_control_catalog.py` — IMPLEMENTED/NOT_IMPLEMENTED/UNKNOWN three-state assessors (reused by nist_matrix). |
| ConMon (continuous monitoring) | **IMPLEMENTED_UNVERIFIED** | `backend/security/helm_conmon.py` + `backend/conmon_manager.py` (160 lines). |
| Zero-trust | **IMPLEMENTED_UNVERIFIED / PARTIAL** | `backend/security/zero_trust/` — `read_auth.py` (ReadAuthMiddleware), `config.py` (HardenedConfig), `bind_audit.py`, `staged_server.py`, `dev_cert.py`. Both imported into `helm_live_api.py:94-95`. nist_matrix notes read-side auth is **staged, not hot-applied** (honest PARTIAL). |
| ATO / evidence package | **IMPLEMENTED_UNVERIFIED** | `backend/ato_manager.py` (164 lines) — `get_ato_evidence_package`, `create_ato_evidence_zip` (wired in `main.py`). |
| CyberGov scorecard | **IMPLEMENTED_UNVERIFIED** | `backend/cybergov_manager.py` (337 lines); endpoints `/api/v1/cybergov/data`, `/api/v1/cybergov/scorecard` in `backend/main.py:8006+`. |
| NIST map (swarm) | **IMPLEMENTED_UNVERIFIED** | `backend/swarm/nist_map.py` (106 lines), `backend/swarm/cyber_swarm.py`. |
| SBOM / STIG / CVE | **PARTIAL/PLANNED** | `supply_chain.py` in truth layer references supply-chain; keyword hits for sbom/cve are sparse and mostly in docs/prompts, not dedicated scanners. No evidence of a live CVE/SBOM ingestion pipeline. |

⚠️ **Split-brain risk:** security surfaces are spread across **two apps** — `helm_live_api.py` (port 8770; hosts nist_matrix) and `backend/main.py` (hosts cybergov/ato/security endpoints). The Cyber Command Center must pick one canonical host or explicitly federate; today they are not unified.

**Security bottom line:** far more exists than a 51/100 might suggest — a real NIST assessor matrix, control catalog, conmon, zero-trust middleware, ATO packager, cybergov scorecard. This is a **strong foundation to consolidate**, not a blank slate. Main gaps: unify the two hosts, hot-apply read-side auth, and add real SBOM/CVE feeds.

---

## 5. AI GOVERNANCE (model router / provider adapters / cost / hallucination)

| Component | Class | Evidence |
|---|---|---|
| Model router | **IMPLEMENTED_UNVERIFIED** | `backend/model_router/` — `router.py` (data-egress policy check, escalation), `model_registry.py`, `confidence.py`, `escalation_policy.py`, `audit_log.py`, `google_frontier.py`. |
| Provider registry / adapters | **IMPLEMENTED_UNVERIFIED** | `backend/model_provider_registry.py` (DB-backed register/list/get/update), `backend/inference_gateway.py`, `backend/model_gateway.py`, `backend/model_mesh.py`, `backend/multi_model_orchestrator.py`, `backend/agent_model_policy.py`. |
| Data-egress / prompt-injection guard | **PARTIAL** | `router.py::check_data_egress_policy` classifies SECRET/CUSTOMER/FOUNDER_PRIVATE and blocks non-allowed destinations (reads `has_live_project_tracker/data/provider_data_egress_policy.json`). `backend/promptops/prompt_classifier.py`, `backend/prompt_governance.py`. Note: egress check **fails-open** (`return True`) if policy file missing — a gap. |
| Cost tracking | **IMPLEMENTED_UNVERIFIED** | Voice: `backend/voice/cost_gate.py`. Spend: `backend/mission_control/spend_meter.py`, `hoch_ledger.py`. |
| Hallucination tracking | **PARTIAL/ABSENT** | No dedicated `hallucination`-named module in backend. Nearest: `backend/brain_convergence/citation_verifier.py`, `research_scorer.py`, `final_verifier/`, `model_router/confidence.py`. Grounding/citation-verification exists; an explicit hallucination-rate tracker does **not**. |

**AI-governance bottom line:** router + provider registry + cost + egress policy are real. Two honest gaps: egress check fails-open on missing policy, and there is no first-class hallucination-rate metric.

---

## 6. FACTORIES (the 8 factories' observe()/truth paths)

| Component | Class | Evidence |
|---|---|---|
| Factory census engine | **IMPLEMENTED_UNVERIFIED (fresh)** | `backend/mission_control/factory_census.py::census()` — derives each factory's rung from PROVEN evidence (dispatched missions in `swarm_ledger.db`, produced artifacts, checkout URL, revenue via `HochLedger`). Doctrine: "a factory exists at the rung it can PROVE." |
| The 8 factories | **DEFINED** | `FACTORY_INTENT`: HASF (apps/agents, champion EPIC_FURY_2026), HRF (research), HCF (cyber/compliance), HSF (story), HMF (music), HFF (finance) = 6 monetized; HHF (family ops) + HPF (Pods Theater) = 2 **NON_MONETIZED** (exempt from revenue ladder). Total 8. |
| Product registry | **IMPLEMENTED (fresh)** | `coordination/products/product_registry.json` (Jul 17 08:05). Only **HASF/Epic Fury** is at rung 4_SELLABLE with a real charge (`$20.52` gross, net PENDING_SETTLEMENT until 2026-07-21 — rung 5 is NOT yet reached). HFF/HRF/HMF are 3_PRODUCTIZED_DEFINED_ONLY (no checkout). |
| Observe/truth wiring | **IMPLEMENTED_UNVERIFIED** | Census reads `coordination/products/product_registry.json` (path const `PRODUCTS`), artifacts dir, and the mission-control SQLite. Rung verdict = min provable. Census invoked from `helm_live_api.py:367`. |

**Factories bottom line:** the observe/truth path is real and honest — census refuses to over-claim (verdict today: "NO MONETIZED FACTORY IS EARNING"; Epic Fury charge is PROVEN but SETTLEMENT_PENDING, so 0 settled dollars). 8 factories are config-declared; only 1 has ever reached a real charge.

---

## WHAT'S REAL TO BUILD ON vs. WHAT'S A CLAIM

**REAL (build on these — they exist, are fresh, and are honest):**
- Voice interface stack — routes, UI, governance, cost gate, ElevenLabs provider, tests, design docs. ~80% built; needs verify + turn-on, not a rebuild.
- Mission State Engine — single canonical writer, freshly computed, shared by API + voice.
- Runtime truth layer (`backend/truth/*` + `backend/runtime_truth/*`) — mature, fail-closed, freshness-stamped. A genuine differentiator.
- Security seed for Cyber Command Center — `nist_matrix.py` (executable NIST CSF 2.0 × 800-53 assessors), control catalog, conmon, zero-trust middleware, ATO packager, cybergov scorecard.
- Factory census — proves rung from evidence; won't fake-green.

**CLAIM / NOT YET (do not assume these are done):**
- No endpoint verified LIVE this run — the API isn't reachable from the workspace; "live" rests on 2-day-old logs. Verify against the running Mac before building.
- Goal-state critical path is **FAILED due to `No module named pytest`** — validators can't execute; the 51/100 is partly environment rot, not only real gaps.
- ElevenLabs premium voice is **OFF by default** (no key + paid flag) — "voice works" ≠ "premium TTS works."
- Hallucination-rate tracking is **absent** as a first-class metric.
- Data-egress guard **fails-open** if its policy file is missing.
- Security surfaces are **split across two apps** (helm_live_api vs main.py) — no unified Cyber Command Center host today.
- SBOM/CVE/STIG live feeds are **not** present (docs mention, code doesn't implement).
- Only **1 of 6** monetized factories has ever charged; **$0 settled** revenue to date (Epic Fury pending until 2026-07-21).

---

## TOP 5 GAPS TO CLOSE FIRST (before the two big builds)

1. **Fix the validator runtime (pytest missing in Xcode python).** Goal-state critical-path requirements are FAILED with "No module named pytest," poisoning the weighted goal% and much of the 51/100. Restore the toolchain / point validators at a venv with pytest so the goal engine reports REAL state. Highest-leverage, cheapest fix.
2. **Establish a live-verification harness the workspace can trust.** No endpoint could be curled this run (API on the Mac, unreachable from the Linux mount). Add a captured live-probe artifact (or run the probes on the Mac and commit the JSON) so "VERIFIED_LIVE" is provable, not inferred from stale logs. Without this, every "live" claim is really IMPLEMENTED_UNVERIFIED.
3. **Unify the security surface for the Cyber Command Center.** Consolidate nist_matrix (helm_live_api:8770) and cybergov/ato/conmon (main.py) under one canonical host + one truth contract before building the Command Center on top — otherwise it will federate two divergent sources.
4. **Turn on and prove the ElevenLabs premium path (fail-closed today).** Michael pastes the key at a native prompt + sets `paid_providers_allowed`; then capture one real synthesis with a cost line. Voice "executive interface" isn't done until the premium voice is verified, not just coded.
5. **Close the two AI-governance holes:** make `check_data_egress_policy` **fail-closed** when the policy file is missing (today it returns True/allow), and add a first-class hallucination/grounding metric (extend `model_router/confidence.py` + `citation_verifier.py` into a tracked rate). Both are prerequisites for defensibly claiming "AI governance."

---

*Read-only audit. Only file written: this report. No code, config, or state mutated.*
