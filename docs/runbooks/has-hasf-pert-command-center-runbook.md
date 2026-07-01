# Runbook: HAS/HASF PERT Command Center Operations

This runbook guides operators on managing, troubleshooting, and executing the HAS/HASF PERT Command Center.

---

## 1. Core Architecture

The PERT Command Center runs as a standalone FastAPI server on port `8765`. It computes the Critical Path Method (CPM) and Project Evaluation and Review Technique (PERT) parameters dynamically across the 15 core workstreams, reading live agent trust scores and release state data.

```
                  ┌───────────────────────┐
                  │ SQLite: Swarm Ledger  │
                  └───────────┬───────────┘
                              │
                              ▼
┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
│ Local API    │◄───┤  PERT Dashboard   ├───►│  Tailscale   │
│ (Port 8000)  │    │   (Port 8765)     │    │  (Port 3012) │
└──────────────┘    └─────────┬─────────┘    └──────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Operator Cockpit  │
                    └───────────────────┘
```

---

## 2. Dynamic PERT/CPM Formulae

Each task is evaluated using the Beta-Distribution formula:
\[TE = \frac{Optimistic + 4 \times Likely + Pessimistic}{6}\]

Critical path nodes are those where Slack/Float is exactly zero:
\[Slack = Late Finish - Early Finish\]

---

## 3. Operational Tasks

### Starting the Server
```bash
bash scripts/start_pert_command_center.sh
```

### Stopping the Server
```bash
kill $(lsof -t -i:8765)
```

### Verification Checks
```bash
bash scripts/rc32_pert_command_center_verify.sh
```

### Playwright E2E Tests
```bash
E2E_BASE_URL=http://localhost:8765 npx playwright test tests/e2e/rc32-pert-command-center.spec.ts
```

---

## 4. Verification Gates & Integration Metrics

1. **North Star Goal**: Confirms alignment to the baseline release tag (`v0.1.7`).
2. **Executive Readiness**: Monitors completeness against the 15 required workstreams.
3. **RACI Assignments**: Warns if any task is unassigned or has multiple accountable owners.
4. **Security Enforcer**: Validates that port `3012` is isolated and only reachable via Tailscale, preventing public exposure.
5. **No Synthetic Telemetry**: Ensures actual SQLite database rows and local checks are polled. UNKNOWN is rendered if endpoints are down.
