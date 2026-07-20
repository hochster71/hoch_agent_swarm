# W1-002 Pre-Claim Record — Heartbeat Provenance Hardening

Per `HELM_EXECUTION_SCHEDULE_WAVE_1.md` §Mandatory pre-claim repository audit.
No source changes made. Steps 1–2 of the founder burndown order only.

- **Package:** HELM-W1-002 (rescoped: Heartbeat Provenance Hardening)
- **Agent:** Claude · Builder · 2026-07-20
- **Branch:** `helm-runtime-bridge-v1` · HEAD `982bc35b`→ current
- **Execution mode:** `EXTEND_EXISTING` / `HARDEN_EXISTING`
- **Ownership conflict:** none detected on `backend/helm_runtime/collectors.py`.
  ⚠ A Grok session is active in `scripts/kimi/**` — different subsystem, no overlap.

## Search commands and results

```bash
grep -rl -E "st_mtime|produced_at|heartbeat" --include="*.py" backend scripts tests
grep -rn "st_mtime" --include="*.py" backend scripts | grep -iE "fresh|time.time\(\)|now\(\)|age|timestamp"
grep -rn "produced_at" --include="*.py" --include="*.json" backend scripts coordination
```

**`EXISTING_IMPLEMENTATION`** — and materially larger than the package assumed.

## Finding: the defect is systemic, not local

The founder brief scoped this to `HeartbeatFileCollector` and dependent collectors —
2 sites in `collectors.py`. The audit found **46 sites deriving freshness from
filesystem mtime**, across 12+ modules:

| File | Sites | Significance |
|---|---:|---|
| `backend/helm_live_api.py` | **19** | **serves the live API, incl. council router** |
| `backend/voice/extended_factories.py` | 6 | voice-surfaced freshness labels |
| `backend/voice/briefing.py` | 5 | founder briefing freshness |
| `backend/helm_runtime/collectors.py` | 2 | the two sites originally scoped |
| `scripts/verify_runtime_truth_freshness.py` | 1 | **the freshness verifier itself** |
| `backend/truth/{wall_state,hmai,external_milestones}.py` | 3 | truth layer |
| `scripts/goal/{goal_engine,verify_champion_gates}.py` | 2 | **feeds the burndown** |
| others | 8 | — |

### Three consequences that change the plan

1. **REQ-ES-004 cannot be satisfied by fixing `collectors.py` alone.**
   `helm_live_api.py` holds 19 mtime-freshness sites and mounts `council_router`
   (line 87–88). The endpoint intended to *serve* freshness evidence is itself built on
   the substitution being removed. Serving it unfixed would produce an authoritative-
   looking `age_seconds` derived from file touch time.

2. **The freshness verifier is itself affected.**
   `scripts/verify_runtime_truth_freshness.py:116` computes evidence age from mtime.
   The tool that checks freshness would pass a forged-mtime file. Same defect class as
   `integration_state()` returning INTEGRATED for an 8-char prefix.

3. **The burndown reads its own inputs through the substitution.**
   `scripts/goal/goal_engine.py:75` and `verify_champion_gates.py:60` age their evidence
   by mtime. Any `git checkout`, `pull`, `stash pop`, or rsync refreshes those files
   without refreshing their content — which means today's `90%` / `100%` figures were
   computed against ages that a VCS operation can reset. Several such operations were
   performed in this repository today.

### Producer contract: partially present, unpopulated

`backend/final_verifier/runtime_truth_contract.py:67` already defines
`is_fresh(evidence_kind, produced_at_epoch)` — the correct shape exists. But
`coordination/goal/HELM_PROMOTION_EVIDENCE_MANIFEST.json` carries
`"produced_at": null` on every entry. The contract was designed and never fed.
This is `EXTEND_EXISTING`, not `NEW_IMPLEMENTATION`.

## Recommended rescope (founder decision required)

The burndown order remains correct; the sizing does not. Proposed split:

| Item | Scope | Note |
|---|---|---|
| **W1-002a** | `collectors.py` (2 sites) + failing tests + producer contract for HELM daemons | as briefed; small |
| **W1-002b** | `helm_live_api.py` (19 sites) | **blocks REQ-ES-004**; must precede it |
| **W1-002c** | `verify_runtime_truth_freshness.py`, `goal_engine.py`, `verify_champion_gates.py` | the burndown's own inputs |
| **W1-002d** | voice/briefing surfaces (11 sites) | founder-visible, lower risk |

Doing only W1-002a and then serving REQ-ES-004 would satisfy the letter of the
acceptance gates while the endpoint still reported mtime-derived ages. That is the
failure mode this package exists to remove.

## Baseline tests (must stay green)

```
tests/unit/test_collectors.py            21 passed
tests/unit/test_mission_envelope.py      17 passed
tests/unit/test_kimi_redaction_gaps.py   20 passed
tests/unit/test_integration_state.py     15 passed
```

## State

`ASSIGNED` — steps 1–2 only. Step 3 (remove mtime fallback) not started pending the
rescope decision above, because the correct blast radius is now a founder call rather
than an implementation detail.
