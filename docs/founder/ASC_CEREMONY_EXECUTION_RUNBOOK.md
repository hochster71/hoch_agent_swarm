# ASC Ceremony Execution Runbook

**Audience:** Founder (Michael Hoch) only.
**Status:** Read-only reference. This document grants no authority and records no state.
**Scope:** App Store Connect credential ceremony for EPIC_FURY_2026 (`com.epicfury.dashboard`) and its read-only post-ceremony verification.

---

## Phase 1 — Founder ceremony

```bash
cd ~/hoch_agent_swarm
.venv/bin/python scripts/founder/asc_credentials_gate.py
```

This step requires founder interaction and founder credentials (App Store Connect Key ID, Issuer ID, and the path to the `AuthKey_*.p8` file). **It must not be executed by an agent.** Prompts are hidden; nothing pasted is echoed, logged, or transmitted anywhere except to Apple's App Store Connect API for validation. Raw private-key material is never persisted; only the `.p8` file *path* is stored (in the gitignored `.env`, mode 600). Before entering credentials, confirm screen sharing and terminal session recording are disabled.

On genuine Apple authentication the gate writes the evidence snapshot, an atomic ceremony receipt (`coordination/evidence/external/asc_ceremonies/<ceremony_id>.json`), appends the ceremony ledger, and re-runs the champion-gate, shipped, and goal-engine recomputes with each step's exit code and output digests recorded honestly in the receipt. On any validation failure it exits fail-closed and persists nothing.

## Phase 2 — Read-only verification

```bash
.venv/bin/python scripts/goal/verify_post_asc_ceremony.py
```

Expected exit behavior:

Exit `0` means all evidence checks passed — receipt-store integrity, ceremony identity correlation, snapshot and gate-script digest binding, per-step recompute binding, freshness, replay/rollback protection, exact Apple acceptance-state policy, and the verifier's own no-mutation proof — while **overall governance may still remain WITHHELD** (N3 independent verification and the Security High finding are separate gates).

Exit `1` means one or more checks failed closed: missing, malformed, stale, duplicated, rolled-back, digest-mismatched, uncorrelated, or policy-inconsistent evidence. The printed board states each failure's source artifact, digest, timestamp, parsed value, and reason.

An exit code of `0` does **not** grant founder release, independent evidence admission, or operational qualification. It confirms only that the ceremony's evidence chain is internally sound.

## Phase 3 — Evidence review

Inspect these authoritative artifacts, in this order:

| Evidence | Path |
|---|---|
| Ceremony receipt (active) | `coordination/evidence/external/asc_ceremonies/<ceremony_id>.json` |
| Ceremony ledger | `coordination/evidence/external/asc_ceremonies/LEDGER.jsonl` |
| Apple evidence snapshot | `coordination/evidence/external/asc_epic_fury.json` |
| Champion gates (TESTFLIGHT / APP_STORE_CONNECT) | `coordination/goal/champion_gates.json` |
| Goal state (REQ-CP-APP_STORE_CONNECT, REQ-TO-002) | `coordination/goal/goal_state.json` |
| Mission state projection | `coordination/goal/mission_state.json` |
| Shipped report (REQ-TO-002) | `coordination/goal/shipped_report.json` |
| PERT / build-to-goal | `coordination/goal/helm_pert.json`, `coordination/goal/build_to_goal_status.json` |
| Doorstep packet | `coordination/goal/intake_to_doorstep.json` |
| Verifier output | terminal output of Phase 2 (re-run at will; it is read-only) |

Known limitations, disclosed: receipts are digest- and ledger-bound, **not cryptographically signed** — there is no signer nonrepudiation. PERT and doorstep artifacts carry no native ceremony identifier; their correlation to the ceremony is temporal against the active receipt and is labeled as such in the verifier output.
