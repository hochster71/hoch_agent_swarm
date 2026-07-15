# HELM Mission State Engine

**Status:** LIVE (derived artifact + API)  
**Artifact:** `coordination/goal/mission_state.json`  
**Doctrine:** no_fake_green · single operational truth · model-agnostic

---

## Purpose

Coding agents answer: *“Did I write the code?”*  

**HELM answers:** *“What is the current operational state of the mission?”*

Mission state includes engineering, testing, security, evidence, approvals, distribution, and revenue — **one document** for every interface.

---

## Architecture

```
goal_engine / champion_gates / conmon / revenue ledger
                    │
                    ▼
         Mission State Engine
    backend/mission_control/mission_state.py
                    │
                    ├── coordination/goal/mission_state.json
                    │
        ┌───────────┼───────────┬────────────┐
        ▼           ▼           ▼            ▼
     Voice API   /mission UI   CLI        Grok tools
```

Builders and routers **update evidence**; the engine **recomputes state**. Interfaces **only read**.

---

## Executive dashboard shape

| Area | Status | Confidence |
|------|--------|------------|
| Engineering | % or VERIFIED | High |
| Testing | VERIFIED / … | High |
| Security | VERIFIED / … | High |
| Evidence | VERIFIED / … | High |
| Runtime Truth | VERIFIED / STALE | High |
| Apple Review | Waiting on Founder | Certain |
| Revenue | NOT_STARTED ($0) | Certain |
| Overall Mission | BLOCKED_EXTERNAL | High |

Critical path marks: Engineering ✓ · Security ✓ · Evidence ✓ · Founder ⏳ · Apple ⏳ · Release ⏳

---

## Endpoints

| Method | Path | Use |
|--------|------|-----|
| GET | `/api/v1/helm/mission` | JSON mission state |
| GET | `/api/v1/helm/mission/executive` | Plain-text dashboard |
| GET | `/api/v1/helm/voice/mission` | Voice/Grok speech + dashboard |
| GET | `/mission` | Mobile executive UI |
| CLI | `python scripts/goal/write_mission_state.py` | Refresh + print |

Voice command: **mission_ops** (“mission status”, “executive dashboard”, “are we ready to ship?”).

Goal engine writes mission state after each successful compute.

---

## Rules

1. Never invent Apple/TestFlight green without ASC evidence.  
2. Monetization gate PASS ≠ revenue.  
3. Founder-only gates surface as PENDING / BLOCKED_EXTERNAL.  
4. All UIs/voice/Grok must prefer this state over free-form model narrative.
