# HELM Execution Schedule — Wave 1

Status: APPROVED FOR IMMEDIATE PICKUP
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

## Wave 1 immediate execution queue

### HELM-W1-001 — Mission Instrumentation SDK

Priority: P0
Owner role: Runtime Agent
Dependency: None
Approved paths:
- `helm/telemetry/`
- `helm/mission/`
- `schemas/mission_envelope.schema.json`
- dedicated tests and documentation

Required outcomes:
- immutable mission IDs;
- append-only events;
- automatic capture of agent, model, host, PID, repository, task, sources, mutations, unknowns, errors, and Founder gates;
- before/after hashing where applicable;
- atomic writes and schema validation;
- derived status only; caller-supplied status must be rejected;
- deterministic unit and negative tests.

Exit evidence:
- files changed;
- test commands and exact results;
- commit SHA and tree SHA;
- limitations;
- integration and rollback instructions.

### HELM-W1-002 — Engineering Telemetry Adapter

Priority: P0
Owner role: Telemetry Agent
Dependency: HELM-W1-001 interface contract; implementation may begin with a local adapter contract.
Approved paths:
- `helm/adapters/engineering_adapter.py`
- `helm/collectors/git_collector.py`
- `helm/collectors/process_collector.py`
- `helm/collectors/task_collector.py`
- dedicated tests

Required outcomes:
- strictly read-only Git branch, HEAD, tree, worktree, diff, recent commit, and worktree telemetry;
- active process, command, test, task, lock, log, failure, and freshness observations;
- authoritative source references;
- no inference of useful progress from process existence alone;
- fail-closed handling for missing, stale, or conflicting data.

### HELM-W1-003 — Founder Live Hardening

Priority: P0
Owner role: Founder Live UI Agent
Dependency: Existing Founder Live interfaces; do not alter shared runtime contracts without explicit integration approval.
Approved paths:
- `scripts/helm_founder_live.py`
- `scripts/helm_live_run_collector.py`
- `frontend_live/live_run.html`
- dedicated Founder Live tests/docs

Required outcomes:
- `$0` revenue renders neutral unless a verified positive target is met;
- field-level evidence grades;
- source, timestamp, freshness, confidence, and provenance per claim;
- distinct `UNATTESTED`, `UNKNOWN`, `STALE`, `CONFLICT`, and `UNAVAILABLE` states;
- Why/provenance inspector;
- event search and replay;
- collector-health panel;
- WebSocket reconnect and stale-stream behavior;
- live update tests without restart.

### HELM-W1-004 — HEOS Qualification Adapter

Priority: P1
Owner role: Qualification Agent
Dependency: Engineering telemetry contract
Approved paths:
- `helm/adapters/heos_adapter.py`
- `heos/evidence_readers/`
- `heos/schemas/`
- dedicated tests

Required outcomes:
- read-only candidate commit/tree identity;
- Gate 0 completeness result;
- test counts and exit codes;
- integrity, governance, promotion, baseline lineage, supersession, and Founder decision status;
- no mutation of active qualification logic.

### HELM-W1-005 — Knowledge Graph Foundation

Priority: P1
Owner role: Knowledge Agent
Dependency: Mission Instrumentation SDK schema
Approved paths:
- `helm/knowledge_graph/`
- `schemas/helm_graph_*.json`
- dedicated tests/docs

Required outcomes:
- entity model for Mission, Factory, Agent, Evidence, Decision, Test, Repository, Product, and Founder Gate;
- typed relationships and provenance;
- deterministic graph ingestion;
- impact and dependency queries;
- no replacement of authoritative source artifacts;
- initial Why-path traversal API.

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

## Non-interference contract

Every agent must:

1. Capture repository root, branch, HEAD, tree, worktree status, and active worktrees before editing.
2. Work only in explicitly approved ownership paths.
3. Stop with `OWNERSHIP_CONFLICT` if an approved path is already being modified by another task.
4. Never stage, unstage, revert, reset, move, delete, format, merge, or overwrite another agent's work.
5. Avoid `.gitignore`, lockfiles, global configuration, deployment configuration, secrets, production services, and shared runtime schemas unless explicitly assigned.
6. Prefer a dedicated worktree and task branch.
7. Keep commits path-scoped.
8. Do not merge or cherry-pick into the shared branch.
9. Return exact evidence and controlled integration instructions.
10. Render missing or stale state honestly; no fake green.

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
- automated merges or cherry-picks.

## Required pickup protocol

An agent accepting a package must post:

- package ID;
- agent/model identity;
- branch and worktree;
- approved paths;
- preflight HEAD/tree/status;
- evidence-qualified state `ASSIGNED`;
- expected integration dependencies;
- any ownership conflict.

Updates are mandatory at `BUILT`, `TESTED`, `INTEGRATION_PENDING`, `INTEGRATED`, `LIVE_VERIFIED`, or `BLOCKED`.

## Founder acceptance for HELM Alpha

- all HELM domains have explicit telemetry state or formal deferral;
- engineering, qualification, factory, and deployment telemetry come from authoritative sources;
- Founder Live shows provenance and freshness;
- mission instrumentation is used by new HELM agents;
- resilience negative tests pass;
- no unsupported green states;
- controlled integration evidence is complete.
