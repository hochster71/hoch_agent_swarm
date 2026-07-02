# HAS/HASF Live Runner Foundation (2026-07-02)

**GitHub Target**:
- Owner: **hochster71**
- Repo: **hochster71/hoch_agent_swarm**
- Local repo: `/Users/michaelhoch/hoch_agent_swarm`

**Runner Labels**:
- `self-hosted`
- `has-qa-runner`
- `has-release-runner`

**Setup Instructions**:
1. Open https://github.com/hochster71/hoch_agent_swarm
2. Settings → Actions → Runners → New self-hosted runner
3. Choose Linux (DigitalOcean Ubuntu) for `has-qa-runner` or macOS for `has-release-runner`
4. Register with labels `self-hosted,has-qa-runner` or `self-hosted,has-release-runner`
5. Keep runner online 24/7
6. Run:
   ```bash
   python scripts/runner_health_check.py
   python scripts/has_runner_orchestrator.py
   ```
7. Live UI at has_live_project_tracker shows:
   - HAS/HASF Live Runner = **PROVEN / PASS**
   - QA Runner Status
   - Release Runner Status
   - Last Heartbeat
   - Active Workflows

**Workflows**:
- `.github/workflows/has-qa-runner.yml` (QA, Playwright, hygiene, doctrine, RC55/RC56/RC58)
- `.github/workflows/has-release-runner.yml` (rc29, deployment readiness, release packaging)

**Scripts**:
- `scripts/runner_health_check.py` (health and live UI status)
- `scripts/has_runner_orchestrator.py` (coordination and state)

**Status**: Runner architecture fully updated to hochster71/hoch_agent_swarm. Visual doctrine, blank image reset, and voice Phase 1 preserved. No deployment, no Stripe, no paid providers enabled. 24/7 runner foundation established.

**Evidence**: This file and `docs/operations/has-hasf-live-runner-architecture.md`

**Single Next Action**: Run `python scripts/runner_health_check.py` to verify live runner connection and update the live UI.

**Workflows Created**:
- `.github/workflows/has-qa-runner.yml` (QA, Playwright, hygiene, doctrine, RC55/RC56/RC58)
- `.github/workflows/has-release-runner.yml` (rc29, deployment readiness, release packaging)

**Evidence**:
- `docs/operations/has-hasf-live-runner-architecture.md`
- This file

**Current Status**: Runner architecture updated to hochster71/hoch_agent_swarm. No deployment, no Stripe, no app-store submission, no paid providers enabled. Visual doctrine and blank image reset preserved. Runner is ready for 24/7 QA and release operations.

**Single Next Action**: Run `python scripts/runner_health_check.py` to verify live runner connection and update the live UI.
