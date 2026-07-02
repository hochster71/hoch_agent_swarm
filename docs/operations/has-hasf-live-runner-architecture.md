# HAS/HASF Live Runner Architecture

**GitHub Target**:
- Owner: **hochster71**
- Repo: **hochster71/hoch_agent_swarm**
- Local repo: `/Users/michaelhoch/hoch_agent_swarm`

**Runner Labels**:
- `self-hosted`
- `has-qa-runner` (for QA, Playwright, baseline, hygiene, doctrine checks)
- `has-release-runner` (for rc29, deployment readiness, release packaging)

**Runner Setup**:
1. Open GitHub repo: https://github.com/hochster71/hoch_agent_swarm
2. Go to **Settings → Actions → Runners → New self-hosted runner**
3. Choose OS:
   - Linux (DigitalOcean Ubuntu droplet) for has-qa-runner
   - macOS (local Mac) for has-release-runner
4. Register with labels: `self-hosted,has-qa-runner` or `self-hosted,has-release-runner`
5. Keep runner online 24/7.
6. Run health check:
   ```bash
   python scripts/runner_health_check.py
   python scripts/has_runner_orchestrator.py
   ```
7. Live UI shows:
   - HAS/HASF Live Runner = **PROVEN / PASS**
   - QA Runner Status
   - Release Runner Status
   - Last Heartbeat
   - Active Workflows

**Workflows**:
- `.github/workflows/has-qa-runner.yml` (QA, Playwright, hygiene, doctrine, RC55/RC56/RC58)
- `.github/workflows/has-release-runner.yml` (rc29, deployment readiness, release packaging)

**Evidence**:
- `docs/evidence/runtime/has-hasf-live-runner-foundation.md`

**Status**: Runner architecture updated to hochster71/hoch_agent_swarm. No deployment performed. No Stripe, no app-store submission, no paid providers enabled. Visual doctrine and blank image reset preserved.

**Single Next Action**: Run `python scripts/runner_health_check.py` to verify live runner connection.
