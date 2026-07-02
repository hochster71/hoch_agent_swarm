# HAS/HASF Executive Automation Scope Lock

**Doctrine ID**: HAS_HASF_EXECUTIVE_AUTOMATION_SCOPE_LOCK_v1

**HAS**:
Live autonomous command/control layer for agents, QA gates, runtime truth, approvals, telemetry, evidence, stale detection, and operator alerts.

**HASF**:
Revenue-directed software factory that turns agent work into deployable products, APIs, apps, evidence packs, and monetizable releases.

**North Star**:
Michael becomes executive approver, not manual operator. HAS/HASF continuously audits itself, runs safe automation, blocks risky actions, updates the live UI at http://127.0.0.1:8765/, and moves products toward revenue.

**Allowed Autonomous Actions**:
- Run QA gates, hygiene checks, doctrine guards, Playwright tests, frontend build, rc29 verify, baseline scans
- Detect stale agents, update live UI with runtime truth
- Produce exactly one next action in operator queue
- Write evidence to docs/evidence/runtime/
- Update machine-readable audit JSON files
- Run local runner health checks

**Blocked Actions Requiring Michael Approval**:
- Deployment
- Stripe/live monetization
- Apple/Google Play submission
- Paid provider enablement
- Visual authority changes
- Destructive changes
- New voice providers (xAI realtime, etc.)
- Any change that increases Michael manual burden

**Drift Sources**:
- Feature creep
- Multiple competing next actions
- Fake-green status
- Image authority drift
- Unproven 24/7 claims
- Unproven deployment readiness

**Anti-Drift Rules**:
- Always exactly one next action
- Missing proof = NOT PROVEN (not green)
- Michael role = EXECUTIVE_APPROVER_ONLY
- Runner must prove automation against http://127.0.0.1:8765/
- All changes must pass scope lock guard

**Success Metrics**:
- Michael manual facilitation reduced to approval only
- Live UI shows runtime truth, stale agents, QA gates, PERT, revenue blockers
- Exactly one next action at all times
- No fake-green status
- Scope lock guard always PASS

**Runner Purpose**:
Automate QA, tests, hygiene, evidence, live UI updates, and safe actions against localhost:8765. Not to replace Michael approval for high-risk changes.

**Live UI Truth-Source Requirements**:
- All panels must source from machine-readable JSON (has_live_project_tracker/data/)
- No hardcoded status
- Missing data must show NOT PROVEN
- No image resurrection

This contract supersedes all previous scope creep. All work must pass `scripts/verify_has_hasf_scope_lock.py`.

**Single Next Action Policy**: Always exactly one next safe action. Risky actions go to human_approval_queue.json.
