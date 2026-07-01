# RC26 — Relay Routing Integration Evidence

**Epic:** HOCH-200  
**RC:** RC26  
**Branch:** rc26-has-hasf-relay-routing  
**Date:** 2026-07-01  
**Author:** automated (antigravity/RC26)

---

## Gate Table

| Check | Status | Detail |
|-------|--------|--------|
| relay-adapter-module | PASS | `backend/relay_worker_adapter.py` created, syntax OK |
| relay-adapter-unknown-on-failure | PASS | `_get_json()` returns `None` on all exceptions; `get_relay_worker_status()` returns `"UNKNOWN"` when health is `None` |
| relay-adapter-no-pass-synthesis | PASS | Only `raw_status == "ONLINE"` returns `"ONLINE"`; all else → `"UNKNOWN"` |
| capability-router-relay-001 | PASS | `RELAY-001: ["relay", "heartbeat", "api"]` added to `CORE_NODE_CAPABILITIES` |
| capability-router-relay-tasks | PASS | `task_type in ("relay_forward", "heartbeat", "relay")` routes to `relay` capability |
| relay-routing-policy-json | PASS | `config/relay_routing_policy.json` created, JSON valid |
| cluster-worker-profiles-relay | PASS | `hoch-relay-001` profile added to `config/cluster_worker_profiles.json` |
| main-py-relay-health-endpoint | PASS | `GET /api/v1/relay/health` registered, syntax OK |
| main-py-relay-registry-endpoint | PASS | `GET /api/v1/relay/registry` registered, syntax OK |
| main-py-relay-status-endpoint | PASS | `GET /api/v1/relay/status` registered, syntax OK |
| main-py-port-public-false | PASS | `port_public_exposed: False` hardcoded in all relay endpoints |
| tracker-status-relay-workers | PASS | `relay_workers` key added to `has_live_project_tracker/data/status.json` |
| tracker-status-option-a | PASS | Separate `relay_workers` key — tracker process writes only to `agents` |
| accountability-seed-script | PASS | `scripts/seed_relay_accountability.py` created, idempotent |
| main-py-syntax | PASS | `python3 -m py_compile backend/main.py` → OK |
| relay-adapter-syntax | PASS | `python3 -m py_compile backend/relay_worker_adapter.py` → OK |
| seed-script-syntax | PASS | `python3 -m py_compile scripts/seed_relay_accountability.py` → OK |
| profiles-json-valid | PASS | `python3 -m json.tool config/cluster_worker_profiles.json` → OK |
| policy-json-valid | PASS | `python3 -m json.tool config/relay_routing_policy.json` → OK |
| status-json-valid | PASS | `python3 -m json.tool has_live_project_tracker/data/status.json` → OK |

---

## API Contract Proof

### Relay adapter module
- **File:** `backend/relay_worker_adapter.py`
- **Endpoints proxied:** `/health`, `/api/registry`
- **Timeout:** 3 seconds
- **UNKNOWN gate:** `_get_json()` catches `URLError`, `JSONDecodeError`, and bare `Exception` — all return `None`
- **Status normalisation:** `"ONLINE" if raw_status == "ONLINE" else "UNKNOWN"` — no other values pass

### Backend proxy endpoints
```
GET /api/v1/relay/health    → fetch_relay_health() → normalised {worker_status: "ONLINE"|"UNKNOWN"}
GET /api/v1/relay/registry  → fetch_relay_registry() → {workers: [...]} or {workers: [], reachable: false}
GET /api/v1/relay/status    → get_relay_combined_status() → full merged payload
```

All three endpoints catch bare `Exception` and return `worker_status: "UNKNOWN"` — they never raise HTTP 500 for relay failures.

---

## Routing Policy Proof

```json
// config/relay_routing_policy.json (key fields)
{
  "worker_id": "HAS-WORKER-RELAY-001",
  "node_id": "RELAY-001",
  "eligible_task_types": ["relay_forward", "heartbeat", "relay"],
  "eligible_capabilities": ["relay", "heartbeat", "api"],
  "constraints": {
    "require_tailscale": true,
    "port_public_exposed": false
  }
}
```

```python
# backend/capability_router.py (added)
"RELAY-001": ["relay", "heartbeat", "api"],  # CORE_NODE_CAPABILITIES

# RC26: Check for relay/heartbeat tasks — route to RELAY-001
if task_type in ("relay_forward", "heartbeat", "relay") or "relay" in prompt_lower or "heartbeat" in prompt_lower:
    req_caps.append("relay")
    return req_caps
```

---

## Tracker Status Seed Proof

```json
// has_live_project_tracker/data/status.json (relay_workers key, Option A)
{
  "relay_workers": [{
    "id": "HAS-WORKER-RELAY-001",
    "name": "Relay Worker (hoch-relay-001)",
    "status": "UNKNOWN",
    "status_source": "/api/v1/relay/health",
    "tailscale_ip": "100.87.18.15",
    "relay_port": 3012,
    "port_public_exposed": false,
    "epic": "HOCH-200"
  }]
}
```

Status is `UNKNOWN` at rest. The tracker frontend polls `/api/v1/relay/health` for live state.

---

## Accountability Seed Proof

- **Script:** `scripts/seed_relay_accountability.py`
- **Baseline score:** 80 (Tier 4: Trusted Autonomous)
- **Tier:** GOLD
- **Idempotent:** `INSERT OR IGNORE` — safe to re-run
- **Usage:** `python3 scripts/seed_relay_accountability.py`

---

## Commit Log

| Commit | Message | Files |
|--------|---------|-------|
| b64e405 | feat(rc26): add relay worker adapter module | `backend/relay_worker_adapter.py` |
| 1f21062 | feat(rc26): add relay routing policy and extend capability router | `config/relay_routing_policy.json`, `backend/capability_router.py`, `config/cluster_worker_profiles.json` |
| 978b1f5 | feat(rc26): add relay backend proxy endpoints | `backend/main.py` |
| a2a8ebe | feat(rc26): seed relay worker into tracker status.json | `has_live_project_tracker/data/status.json` |
| 2ff7840 | feat(rc26): add accountability seed script for relay worker | `scripts/seed_relay_accountability.py` |

---

## FINAL_GO Checklist

- [x] Relay adapter returns UNKNOWN on failure — never synthesises ONLINE
- [x] Port 3012 never exposed publicly — `port_public_exposed: False` hardcoded
- [x] No secrets committed — RELAY_BASE_URL via env var, default is Tailscale IP only
- [x] Unknown provider states render UNKNOWN — enforced in adapter and all 3 endpoints
- [x] Local runtime not replaced — relay is additive; L1 remains default fallback
- [x] Relay task types registered: relay_forward, heartbeat, relay
- [x] RELAY-001 registered in capability router
- [x] Relay profile in cluster_worker_profiles.json
- [x] Tracker status.json seeded with relay_workers (Option A — separate key)
- [x] Accountability seed script ready
- [x] All Python files syntax-clean
- [x] All JSON files valid
- [ ] E2E Playwright tests run (C7)
- [ ] Manual backend smoke test (post-deploy)
- [ ] `python3 scripts/seed_relay_accountability.py` run on local backend

**Gate: CONDITIONAL_GO** — pending E2E test execution and manual smoke.
