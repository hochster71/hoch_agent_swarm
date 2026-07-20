# HELM Execution Schedule — Wave 1

Status: APPROVED FOR IMMEDIATE PICKUP — CORRECTED FOR EXISTING IMPLEMENTATIONS
Founder: Michael Bryan Hoch
Repository: `hochster71/hoch_agent_swarm`
Base branch: `rc21-ci-enforced-security`
Execution branch: `helm/execution-schedule-wave-1`

## North Star

Deliver HELM as a trustworthy, observable, governed operating system through:

`TRUTH -> OBSERVABILITY -> EXECUTION -> GOVERNANCE -> RESILIENCE -> FOUNDER CONTROL`

## Mandatory lifecycle

Every work package must move through:

`BACKLOG -> ASSIGNED -> BUILT -> TESTED -> INTEGRATION_PENDING -> INTEGRATED -> LIVE_VERIFIED`

No agent may claim plain `COMPLETE` without scope-qualified evidence.

## Mandatory pre-claim repository audit

Before claiming or implementing any package, the assigned agent must inspect the repository for existing implementations, tests, schemas, adapters, collectors, interfaces, and architectural decision records.

The pickup record must include:

- search commands or indexed queries used;
- existing implementation paths found;
- existing tests and current results;
- whether the task is `EXTEND_EXISTING`, `HARDEN_EXISTING`, `MIGRATE_EXISTING`, or `NEW_IMPLEMENTATION`;
- explicit justification when no implementation exists;
- an `OWNERSHIP_CONFLICT` stop when another agent is changing the same subsystem.

A new parallel subsystem may not be created merely because the roadmap names a different path. Existing authoritative implementations must be extended unless a reviewed migration decision explicitly deprecates the old location.

## Verified existing implementation baseline

The following existing implementation claims were identified during third-agent inspection and must be verified locally by the claiming agent before modification:

- `backend/helm_runtime/mission_envelope.py` — existing mission-envelope and derived-status implementation;
- `backend/helm_runtime/collectors.py` — existing Git and process collectors;
- existing adversarial tests for mission-envelope behavior;
- existing embedded/in-module schema behavior where applicable.

These paths are the presumptive authoritative baseline. If a claiming agent cannot locate them in its checked-out ref, it must report `BASELINE_MISMATCH` with branch, HEAD, and search evidence rather than creating replacements.

## Governance prerequisite

Founder Live hardening may proceed only after the current governance and evidence-decision records affecting Founder Live are inventoried and their ratification/audit status is displayed. UI work must not silently convert unratified design decisions into authoritative runtime policy.

## Wave 1 immediate execution queue

### HELM-W1-001 — Mission Instrumentation Runtime Hardening

Priority: P0
Owner role: Runtime Agent
Dependency: Existing `backend/helm_runtime` implementation and tests
Execution mode: `EXTEND_EXISTING` / `HARDEN_EXISTING`
Approved paths:
- `backend/helm_runtime/mission_envelope.py`
- directly associated existing schema modules
- directly associated existing tests
- dedicated documentation

Required outcomes:
- inventory current capabilities before editing;
- preserve immutable mission IDs and append-only events;
- preserve automatic capture of agent, model, host, PID, repository, task, sources, mutations, unknowns, errors, and Founder gates where already implemented;
- preserve or strengthen before/after hashing, atomic writes, and schema validation;
- preserve derived status and rejection of caller-supplied status;
- close known test failures and coverage gaps rather than rebuild the subsystem;
- document the canonical public interface and deprecate no path without an approved migration record;
- add deterministic unit, integration, and adversarial tests for any uncovered behavior.

Prohibited:
- creating parallel `helm/telemetry/` or `helm/mission/` implementations unless an approved migration ADR explicitly authorizes it;
- weakening existing adversarial tests;
- claiming completion while baseline tests fail.

Exit evidence:
- baseline inventory;
- files changed;
- before/after test commands and exact results;
- commit SHA and tree SHA;
- limitations;
- integration and rollback instructions.

### HELM-W1-002 — Engineering Telemetry Coverage Expansion

Priority: P0
Owner role: Telemetry Agent
Dependency: Existing `backend/helm_runtime/collectors.py` and mission-envelope contract
Execution mode: `EXTEND_EXISTING` / `HARDEN_EXISTING`
Approved paths:
- `backend/helm_runtime/collectors.py`
- existing directly associated adapter/collector modules discovered during pre-claim audit
- directly associated tests
- dedicated documentation

Required outcomes:
- inventory existing `GitCollector`, `ProcessCollector`, and related collectors;
- preserve strictly read-only Git branch, HEAD, tree, worktree, diff, recent commit, and worktree telemetry;
- extend coverage for active process, command, test, task, lock, log, failure, daemon heartbeat, and freshness observations;
- detect dead or stale daemons and collectors rather than assuming liveness;
- attach authoritative source references and field-level freshness;
- never infer useful progress from process existence alone;
- fail closed for missing, stale, contradictory, or inaccessible sources;
- add one domain at a time until all ten HELM domains have explicit telemetry state or formal deferral.

Prohibited:
- creating duplicate `helm/collectors/*.py` modules without an approved migration ADR;
- mutating source systems from read-only collectors;
- rendering absent telemetry as healthy.

### HELM-W1-003 — Founder Live Governance and Truth Hardening

Priority: P0
Owner role: Founder Live UI Agent
Dependency: Existing Founder Live interfaces plus governance/EDR inventory
Execution mode: `HARDEN_EXISTING`
Approved paths:
- existing Founder Live implementation paths discovered by pre-claim audit;
- `scripts/helm_founder_live.py` only if it exists and is authoritative;
- `scripts/helm_live_run_collector.py` only if it exists and is authoritative;
- `frontend_live/live_run.html` only if it exists and is authoritative;
- dedicated Founder Live tests/docs.

Required outcomes:
- inventory applicable EDRs/ADRs, including ratification and auditor-verification state;
- display unratified or unaudited governance inputs as such;
- `$0` revenue renders neutral unless a verified positive target is met;
- field-level evidence grades;
- source, timestamp, freshness, confidence, and provenance per claim;
- distinct `UNATTESTED`, `UNKNOWN`, `STALE`, `CONFLICT`, and `UNAVAILABLE` states;
- Why/provenance inspector;
- event search and replay;
- collector-health and daemon-heartbeat panels;
- WebSocket reconnect and stale-stream behavior;
- live update tests without restart;
- no hardening claim while current authoritative tests fail.

### HELM-W1-004 — HEOS Qualification Read Adapter

Priority: P1
Owner role: Qualification Agent
Dependency: Engineering telemetry contract and pre-claim discovery
Execution mode: `EXTEND_EXISTING` when any qualification reader already exists; otherwise `NEW_IMPLEMENTATION`
Approved paths:
- existing qualification/evidence reader paths discovered during pre-claim audit;
- new isolated read-adapter paths only when no equivalent exists;
- dedicated tests/docs.

Required outcomes:
- read-only candidate commit/tree identity;
- Gate 0 completeness result;
- test counts and exit codes;
- integrity, governance, promotion, baseline lineage, supersession, and Founder decision status;
- no mutation of active qualification logic;
- explicit baseline mismatch and stale-evidence handling.

### HELM-W1-005 — Knowledge Graph Foundation

Priority: P1
Owner role: Knowledge Agent
Dependency: Canonical mission-envelope and telemetry schemas
Execution mode: pre-claim discovery required; extend any existing graph implementation
Approved paths:
- existing graph modules discovered during pre-claim audit;
- `helm/knowledge_graph/` only if no authoritative equivalent exists or migration is approved;
- graph schemas and dedicated tests/docs.

Required outcomes:
- entity model for Mission, Factory, Agent, Evidence, Decision, Test, Repository, Product, and Founder Gate;
- typed relationships and provenance;
- deterministic graph ingestion;
- impact and dependency queries;
- no replacement of authoritative source artifacts;
- initial Why-path traversal API;
- duplicate-entity and contradictory-evidence handling.

## Wave 2 queued after Wave 1 evidence gates

- Reasoning Graph Engine
- Runtime Resilience and Recovery
- Memory Architecture
- Agent Performance Analytics
- Voice Platform (`HELM` wake-word abstraction and device-independent pipeline)
- NIST RMF / Continuous ATO Evidence Layer
- Factory Telemetry Standard and Factory SDK
- Digital Twin
- Multi-Model Router
- Autonomous Improvement Agent

No Wave 2 issue is to be opened until its pre-claim repository audit is attached and Wave 1 dependencies are evidence-qualified.

## Non-interference contract

Every agent must:

1. Capture repository root, branch, HEAD, tree, worktree status, and active worktrees before editing.
2. Search for existing implementations before selecting paths.
3. Work only in explicitly approved or discovered authoritative ownership paths.
4. Stop with `OWNERSHIP_CONFLICT` if an approved path is already being modified by another task.
5. Never stage, unstage, revert, reset, move, delete, format, merge, or overwrite another agent's work.
6. Avoid `.gitignore`, lockfiles, global configuration, deployment configuration, secrets, production services, and shared runtime schemas unless explicitly assigned.
7. Prefer a dedicated worktree and task branch.
8. Keep commits path-scoped.
9. Do not merge or cherry-pick into the shared branch.
10. Return exact evidence and controlled integration instructions.
11. Render missing or stale state honestly; no fake green.
12. Never create a duplicate subsystem solely to satisfy a roadmap path.

## Serialized work

The following may not run concurrently without explicit Founder/integration approval:

- broad `backend/main.py` refactors;
- central orchestration runner changes;
- shared queue or schema migrations;
- production database migrations;
- deployment scripts and runtime service changes;
- Stripe, RevenueCat, Vercel, Cloudflare, Apple submission, signing, keys, spend, or money movement;
- active qualification pipeline rewrites;
- global dependency upgrades;
- automated merges or cherry-picks;
- migration from `backend/helm_runtime/` to any new top-level HELM package.

## Required pickup protocol

An agent accepting a package must post:

- package ID;
- agent/model identity;
- branch and worktree;
- pre-claim search commands and results;
- authoritative existing paths found;
- execution mode: `EXTEND_EXISTING`, `HARDEN_EXISTING`, `MIGRATE_EXISTING`, or `NEW_IMPLEMENTATION`;
- approved paths;
- preflight HEAD/tree/status;
- baseline tests and exact results;
- evidence-qualified state `ASSIGNED`;
- expected integration dependencies;
- any ownership conflict or baseline mismatch.

Updates are mandatory at `BUILT`, `TESTED`, `INTEGRATION_PENDING`, `INTEGRATED`, `LIVE_VERIFIED`, `BLOCKED`, `OWNERSHIP_CONFLICT`, or `BASELINE_MISMATCH`.

## Founder acceptance for HELM Alpha

- all HELM domains have explicit telemetry state or formal deferral;
- engineering, qualification, factory, and deployment telemetry come from authoritative sources;
- Founder Live shows provenance, freshness, governance ratification, and auditor-verification state;
- canonical mission instrumentation is used by new HELM agents;
- duplicate implementations are absent or governed by an approved migration record;
- daemon/collector death is detected automatically;
- resilience negative tests pass;
- all authoritative baseline tests pass or failures are explicitly blocked with evidence;
- no unsupported green states;
- controlled integration evidence is complete.
