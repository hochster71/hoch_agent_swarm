# HELM External Engineering Council Runtime — Charter
**2026-07-20 · status: CHARTERED, BUILD DEFERRED (founder decision: finish launch first)**
**Build gate: candidate frozen + promotion-binding qualification complete. Build location: a NEW repository, never this worktree.**

## First principle — trace to demonstrated need (council addition, 2026-07-20)
Every subsystem in the Council Runtime must trace to at least one demonstrated operational need
observed during HELM engineering. Feature-first growth is prohibited. Before any new runtime
component is accepted, four questions must have recorded answers:
1. Which incident justified its existence?
2. Which evidence demonstrates the need?
3. Which failure mode does it eliminate?
4. How will success be measured?
The evidence table below is the founding application of this principle.

## Mission
A model-agnostic orchestration runtime coordinating independent AI engineering systems (Claude
Fable, Claude Opus, GPT-5.5, Grok, Kimi Code Swarm, AG IDE, future members) through: mission
assignment, role assignment, parallel execution, evidence collection, result normalization,
consensus, conflict detection, burndown, security validation, founder gates, and runtime truth.
No logic may depend on a specific vendor or model. Members are plugins with declared identity,
capabilities, cost/context metadata, security classification, and health.

## Why this exists — requirements bound to executed evidence
This charter is not speculative. Every core subsystem maps to a defect this campaign actually
suffered and remediated on 2026-07-19/20. The runtime is the generalization of those fixes:

| Subsystem | Lived incident (evidence) |
|---|---|
| Security Gateway / lane isolation | Two agents sharing one worktree, venv, and git index: BD-F4 (CONCURRENT-EXECUTION-LANE-INTERFERENCE.json) — concurrent suites, sqlite collisions, evidence overwrites, staged-index contamination |
| Evidence Ledger (append-only, atomic) | confirmation_result.json truncated to 0 bytes mid-write by a concurrent lane; fixed by tmp+fsync+rename discipline (now in harvest/evaluator) |
| Baseline integrity / config attestation | BD-F5: acceptance baseline silently emptied by an external writer; fixed by hash-pinning + fail-closed empty-baseline gate + authorization-gated re-pin (re_pin_authorization block) |
| Runtime Truth Engine (fail-closed) | N3-VERDICT-BINDING-GAP: a real VERIFIED verdict applied outside its binding/scope/vintage produced GOAL_REACHED 100%; fixed by _n3_binding_ok (SHA+tree+scope+no-disclaimer or HOLD) |
| Promotion Qualification Engine | run_qualification_suite.sh v2.2 + evaluate_full_suite_acceptance.py: exclusivity monitor with process ancestry+identity, per-run TMPDIR/sqlite isolation, worktree/index hash integrity, rc + parse dual verification, INVALID vs REJECTED vs PASS separation |
| Consensus / Conflict Resolution | Independent adjudications (this session vs AG IDE lane vs Grok) converged and diverged; disagreements resolved by isolated re-execution, never by authority |
| Provenance Tracker | Claim taxonomy (file written ≠ committed ≠ pushed ≠ independently verified) enforced all campaign; every artifact hash-referenced |
| Founder Approval Gateway | Freeze/sign/push/GO/credential actions held founder-only throughout; automation prepares and recommends, never executes them |
| Burndown Engine | burndown_record.json / t1_f1_classification.json: owner, classification, evidence, disposition per failure; no completion without evidence |
| Mission lifecycle state machine | The campaign itself ran the lifecycle by hand: created → planned → decomposed → dispatched (parallel lanes) → evidence → consensus → conflict → validation → founder review |

## Architecture (as specified by the mission prompt, accepted)
Independent, independently-testable services: Council Runtime, Member Registry, Mission Queue,
Mission Planner, Task Scheduler, Context Manager, Prompt Compiler, Evidence Bus, Evidence Ledger,
Consensus Engine, Conflict Resolution Engine, Runtime Truth Engine, Burndown Engine, Dependency
Graph, Critical Path Manager, Security Gateway, Secret Redaction Layer, Provenance Tracker,
Founder Approval Gateway, Promotion Qualification Engine, Audit Logger, Metrics Engine,
Dashboard API, Plugin Framework. Mission lifecycle as an explicit state machine. Consensus =
collect → normalize → compare → score → reconcile → escalate; always explainable.

## Non-negotiable invariants (inherited from this campaign's doctrine)
1. UNKNOWN stays UNKNOWN; missing evidence is never PASS; fail closed everywhere.
2. Every completion claim names its evidence artifact; hashes over narratives.
3. One writer per workspace: members NEVER share a worktree/index/venv (BD-F4 is the proof).
4. Evidence writes are atomic; baselines are hash-pinned; empty/weakened baselines require an
   explicit recorded authorization (BD-F5 is the proof).
5. Verdicts satisfy nothing without proven binding (candidate SHA + tree), scope attestation,
   and vintage (N3 is the proof).
6. Founder-reserved actions (approval, credentials, signing, promotion GO) are architecturally
   outside automated execution — the runtime prepares, validates, recommends only.
7. Secret detection/redaction before any external dispatch; no credentials/PII/controlled
   information in any outbound context.

## Deferred deliverables (build phase, post-launch)
Architecture docs, directory structure, source, tests, plugin SDK, configuration, REST APIs,
event bus, data schemas, examples, dashboards, integration tests, operational runbooks — per the
mission prompt's engineering standard: correctness and auditability over convenience.

## Sequencing record
Founder decision 2026-07-20: "Finish launch first." The finish-don't-expand rule
(HELM_FINAL_EXECUTION_PLAN.md, standing rule 1) holds; this charter is the ONLY runtime-mission
artifact permitted into the candidate tree. The build begins in a fresh repository after the
promotion-binding qualification completes.
