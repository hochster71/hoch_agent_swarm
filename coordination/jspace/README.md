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
| quarantine_request | `ALLOWED` (request only; auto-exec off until burn-in) |
| promotion_authority | `NONE` |

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
| `assessments.jsonl` | Signed (digest-bound) observer assessments |
| `alerts.jsonl` | Alerts for dashboard / founder surfaces |
| `health.json` | Latest meta health snapshot |
| `cycles.jsonl` | Cycle index |
| `quarantine_requests.jsonl` | Requests only — not execution |

## Run

```bash
.venv/bin/python scripts/jspace/run_hjos_cycle.py
.venv/bin/python scripts/jspace/run_hjos_cycle.py --json
```

## Truth classes

Assessments resolve only to:

`CONFIRMED_LIVE` · `UNCONFIRMED` · `STALE` · `UNVERIFIED` · `UNKNOWN` · `BLOCKED` · `CONTRADICTED`

No observer emits `GO` or `AUTHORITATIVE_PASS`.
