# External-milestone evidence snapshots

HELM Design Constitution — **Principle V (Honest Uncertainty)**.

This directory holds **authoritative evidence snapshots** for milestones HELM cannot make
true by itself. `backend/truth/external_milestones.py` reads these files and advances the
RELEASE / REVENUE state machines **only** when the evidence is **present AND fresh**.
Missing, stale, or mismatched evidence **fails closed** to the held state
(`BLOCKED_EXTERNAL` / `PAYMENT_AUTHORIZED`). Expectation is never evidence.

**These files are written by Mac-side pollers/watchers, not by the swarm.** HELM only
reads them. Never hand-edit an "approved"/"settled" state in here to move a milestone —
that would be exactly the FAKE GREEN this whole mechanism exists to prevent.

## Files

### `asc_epic_fury.json` — App Store Connect poller (RELEASE machine)
The Mac-side ASC poller writes the current App Store Connect version state.

```json
{
  "versionString": "1.0.2",
  "appStoreState": "IN_REVIEW",
  "observed_at": "2026-07-17T13:40:00Z"
}
```

`appStoreState` mapping (fresh evidence only; window = 6h):
- `WAITING_FOR_REVIEW` / `IN_REVIEW` / `PENDING_CONTRACT` / prep / rejection / any
  unrecognized state → **BLOCKED_EXTERNAL** (fails closed)
- `APPROVED` → **APPLE_APPROVED**
- `PENDING_DEVELOPER_RELEASE` / `PENDING_APPLE_RELEASE` → **READY_FOR_RELEASE**
- `READY_FOR_SALE` → **LIVE**

### `stripe_settlement.json` — settlement watcher (REVENUE machine)
The 2026-07-21/-22 settlement watcher writes the balance-transaction status for the
Epic Fury first charge.

```json
{
  "charge_id": "ch_3Tsv7qDK7Brrgheo1z3ksuF5",
  "balance_txn_status": "pending",
  "settled_usd": 0,
  "observed_at": "2026-07-17T13:40:00Z"
}
```

- The `charge_id` MUST match `product_registry EPIC_FURY_2026.stripe_charge_id`; a
  mismatch is ignored (fails closed to PAYMENT_AUTHORIZED).
- Only `balance_txn_status == "available"` advances to **SETTLED**.
- **SETTLED → REVENUE_VERIFIED** additionally requires `settled_usd > 0` AND the amount
  booked into the registry (`revenue_settled_usd > 0`).

## Read the live truth
```
python3 -m backend.truth.external_milestones      # from repo root
GET /api/v1/helm/external                          # standard truth envelope
```
