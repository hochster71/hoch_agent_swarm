# DOORSTEP — TestFlight + App Store Connect (FOUNDER ONLY)

**Staged:** 2026-07-15  
**Requirement IDs:** `REQ-CP-TESTFLIGHT`, `REQ-CP-APP_STORE_CONNECT`, `REQ-TO-002`  
**Doctrine:** HELM/voice/agents **must not** clear these. Founder only.

---

## Why this is staged

PERT critical path ends in founder release gates. Agent work can produce packages and evidence; **only Michael** can:

1. Upload/build to **TestFlight**
2. Operate **App Store Connect**
3. Confirm production distribution ship (`REQ-TO-002`)

---

## Preconditions (agent-side — re-check before you act)

```bash
cd /Users/michaelhoch/hoch_agent_swarm
python3 scripts/goal/verify_champion_gate_one.py SECURITY
python3 scripts/goal/verify_champion_gate_one.py BUILD
python3 scripts/goal/verify_champion_gate_one.py TEST
python3 scripts/goal/verify_champion_gate_one.py SUBMISSION_PACKAGE
python3 scripts/goal/goal_engine.py   # refresh goal_state
```

Read:

- `coordination/goal/champion_gates.json`
- `has_live_project_tracker/data/epic_fury_release_ledger.json`
- `docs/evidence/products/epic-fury-2026/`

---

## Founder checklist

### A. TestFlight (`REQ-CP-TESTFLIGHT`)

- [ ] Xcode / Transporter upload of the selected build number from ledger
- [ ] Build appears in App Store Connect → TestFlight
- [ ] Internal testing group can install
- [ ] Drop evidence: screenshot or ASC export path under `docs/evidence/products/epic-fury-2026/`
- [ ] Optional: set env for future automation (never commit secrets):  
      `APP_STORE_CONNECT_KEY_ID`, `APP_STORE_CONNECT_ISSUER_ID`, `ASC_API_KEY` path

### B. App Store Connect (`REQ-CP-APP_STORE_CONNECT`)

- [ ] Listing metadata matches `STORE_METADATA` gate evidence
- [ ] Privacy nutrition labels match `PRIVACY` gate
- [ ] Pricing / availability configured (monetization configured ≠ revenue earned)
- [ ] Submit for review **only** when founder is ready

### C. Ship proof (`REQ-TO-002`)

- [ ] Production distribution state observed (not assumed)
- [ ] Evidence artifact committed under `docs/evidence/products/epic-fury-2026/`
- [ ] Re-run: `python3 scripts/goal/verify_shipped.py` and `goal_engine.py`

---

## Clearance signal for agents

After founder completes a gate, either:

1. Drop `artifacts/handoff/FOUNDER_GATE_CLEARED_<GATE>.txt` with date + evidence path, or  
2. Ensure champion gate validators can observe fresh ASC/TestFlight evidence files.

Agents will re-run `goal_engine.py` — they will **not** mark FOUNDER_ONLY as SATISFIED without validator evidence.
