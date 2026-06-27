# Prompt Audit & Control Backlog

This backlog outlines the required engineering items to mature the Prompt Control Plane across P0, P1, and P2 priority tiers.

## P0 Backlog Items (Core Infrastructure & Safety)

### PR-001: Prompt Governance Wrapper
- **Objective**: Implement a backend middleware or decorator that automatically wraps every loaded prompt with the Universal Agent Execution Contract.
- **Acceptance Criteria**: All prompt requests executed through uvicorn must prepended with the contract rules.

### PR-002: Prompt Router
- **Objective**: Build the dynamic router service to load selected prompt files from the prompt library based on category/industry tags.
- **Acceptance Criteria**: Expose a read-only endpoint that returns prompt chains matching coding or cyber categories.

### PR-003: Human Approval Gate
- **Objective**: Create the dashboard approval queue and API endpoints to hold material actions in a "PENDING" state.
- **Acceptance Criteria**: Material actions return HTTP 202 Accepted and are blocked from execution until a POST approval request is received.

### PR-004: Evidence Contract
- **Objective**: Enforce the generation of `evidence_manifest.json` with SHA-256 hashes at the end of every task execution.
- **Acceptance Criteria**: The ledger database rejects transaction updates if the manifest path is empty or invalid.

### PR-005: Fail-Closed Risk Classifier
- **Objective**: Build a risk assessment function that evaluates incoming task parameters and marks high-risk tasks as blocked.
- **Acceptance Criteria**: Block execution if inputs contain unresolved safety/privacy ambiguity.

### PR-006: Prompt Injection Red-Team Suite
- **Objective**: Develop a local test harness that passes simulated prompt injection payloads to the router and verifies they are blocked.
- **Acceptance Criteria**: Verification tests achieve 100% block rate on injection benchmarks.

### PR-007: ConMon Metrics Dashboard
- **Objective**: Connect the continuous monitoring plan telemetry to frontend UI cards.
- **Acceptance Criteria**: Display Daily, Weekly, and Monthly checklist compliance states.

### PR-008: Known Asset + Agent Runtime Truth Model
- **Objective**: Expand the network scanning daemon to verify active worker heartbeats and API capabilities.
- **Acceptance Criteria**: Distinguish between active, unreachable, and misconfigured model runtimes.

---

## P1 Backlog Items (Automation & Governance Extension)

### PR-009: Prompt Quality Scorer
- **Objective**: Build a scoring utility to evaluate generated outputs against the expected QA contract.

### PR-010: Agent Role Registry
- **Objective**: Define a structured JSON schema mapping agent identities to their allowed prompt roles and scopes.

### PR-011: Task State Machine
- **Objective**: Implement state transitions (PLAN -> DEVELOP -> QA -> RELEASE) in the ledger database.

### PR-012: Ephemeral Pipeline Executor
- **Objective**: Configure isolated, temporary directories for agent tasks that are deleted upon validation.

### PR-013: Release Gatekeeper
- **Objective**: Automate checking of SBOMs and code changes against the release signature rules before committing tags.

### PR-014: App Store Submission Gate
- **Objective**: Implement a manual gate for compiling, packaging, and submitting mobile builds.

### PR-015: Family/Home Privacy Gate
- **Objective**: Scan inputs for private family telemetry and apply masking/redaction filters.

### PR-016: Business/Hobby Mission Templates
- **Objective**: Establish pre-defined prompt chains for software factory operations and hobby tasks.

---

## P2 Backlog Items (optimization & Scale)

### PR-017: Prompt Marketplace/Internal Catalog
- **Objective**: Implement search, tags, and reviews for the 103 prompts in the library.

### PR-018: Model Routing by Task Type
- **Objective**: Dynamically assign tasks to compute workers (Dell vs iMac) based on the task's complexity.

### PR-019: Autonomous Research Team
- **Objective**: Deploy multi-agent subagents to research codebase patterns and documentation in parallel.

### PR-020: Prompt Regression Test Harness
- **Objective**: Compare output quality changes across model updates (Ollama vs cloud fallbacks).

### PR-021: Prompt Drift Detection
- **Objective**: Flag when prompt templates are altered manually without corresponding configuration updates.

### PR-022: Agent Performance Leaderboard
- **Objective**: Track tool failure rates and task success metrics across model engines.
