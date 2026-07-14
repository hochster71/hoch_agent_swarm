# HELM J-SPACE Observability Swarm (HJOS)

**Mission:** Independently observe all HELM agent activity, verify runtime and evidence truth, detect contradictions and unsafe behavior, and provide fail-closed recommendations **without** independently promoting, executing, or rewriting authoritative HELM state.

## Charter

| Capability | Mode |
|---|---|
| default_mode | `READ_ONLY` |
| state_mutation | `PROHIBITED` |
| task_execution | `PROHIBITED` |
| evidence_creation | `ALLOWED` |
| alert_creation | `ALLOWED` |
| quarantine_request | `ALLOWED` (request only) |
| automatic_quarantine | **DISABLED** until founder-approved policy |
| promotion_authority | `NONE` |

Authoritative gate: `coordination/jspace/quarantine_governance.json`

- `automatic_quarantine_enabled` must be `false` unless a founder-approved `authorizing_policy_id` is set
- `orphan_lease_hygiene` defaults to `manual_approval`
- A short burn-in (e.g. five cycles) does **not** authorize mutation
- Clean cycles that only mean “no exception / no self-mutation” are **not** production maturity evidence

## Observers

1. **Truth Sentinel** — false-green, stale, unknown, contradictory, unsupported states  
2. **Flow Sentinel** — leases, locks, balance, expiry, concurrency pressure  
3. **Evidence Auditor** — claims vs on-disk ledgers / artifacts  
4. **Security Sentinel** — control posture, secret-shape scan  
5. **Performance Analyst** — spend window, failure rate, live concurrency  
6. **Meta-Observer** — one governed health assessment per cycle  

## Ledgers (this directory)

| File | Purpose |
|---|---|
| `events.jsonl` | Append-only J-SPACE bus events |
| `assessments.jsonl` | Digest-bound observer assessments |
| `alerts.jsonl` | Alerts for dashboard / founder surfaces |
| `health.json` | Latest meta health snapshot |
| `cycles.jsonl` | Cycle index |
| `incidents.jsonl` | **Immutable** incident lifecycle (OPEN → … → CLOSED by explicit transition only) |
| `quarantine_requests.jsonl` | Requests only — not execution |
| `quarantine_governance.json` | Founder/policy gate for any containment mutation |

Historical findings remain visible after containment. A later `CONFIRMED_LIVE` cycle must **not** erase prior adverse incidents.

## Run

```bash
# one cycle (read-only observation)
.venv/bin/python scripts/jspace/run_hjos_cycle.py
.venv/bin/python scripts/jspace/run_hjos_cycle.py --json

# periodic daemon (default 60s) — still read-only unless policy enables containment
.venv/bin/python scripts/jspace/hjos_daemon.py --interval 60
```

## Wall / API

| Endpoint | Role |
|---|---|
| `GET /api/v1/helm/jspace/health` | Latest meta health + governance |
| `GET /api/v1/helm/jspace/burn-in` | Burn-in tracker (does not authorize mutation) |
| `POST /api/v1/helm/jspace/cycle` | Run one observation cycle |
| PERT wall header | `HJOS: <overall> · alerts · action · promo NONE` |

## Containment (disabled by default)

Automatic quarantine and orphan lease hygiene require:

1. Founder-approved `authorizing_policy_id` in `quarantine_governance.json`
2. Explicit `automatic_quarantine_enabled: true` under that policy
3. Burn-in criteria defined **by that policy** (not a hardcoded five-cycle self-authorization)

Permitted classes (only when policy-enabled):  
`secret_exposure` · `destructive_action` · `founder_gate_bypass` · `evidence_tampering`

## Truth classes

Assessments resolve only to:

`CONFIRMED_LIVE` · `UNCONFIRMED` · `STALE` · `UNVERIFIED` · `UNKNOWN` · `BLOCKED` · `CONTRADICTED`

No observer emits `GO` or `AUTHORITATIVE_PASS`.
