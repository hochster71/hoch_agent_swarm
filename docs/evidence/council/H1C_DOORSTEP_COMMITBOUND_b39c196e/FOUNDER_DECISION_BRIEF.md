# H1C Founder Decision Brief

**Packet binding:** commit `b39c196e5470857a7b8c713de124f6e73b0a7694`  
**Packet SHA-256:** `24eea4eabe7ce3f94fb36a895ffb3351e742d937b8ac7ed717ef30d6032de19a`  
**Validation SHA-256:** `c49e84b325c62e770daad773e2d06ab44fe473de28986785428e04a1db22d0aa`  
**Status at brief creation:** DOORSTEP_READY · PROMOTION LOCKED · SAFE_TO_EXECUTE NO · NOT_GRANTED

This brief does **not** grant authorization. It only frames Michael’s decision.

---

## Requested decision

Choose exactly one:

1. **APPROVE_CONTROLLED_LOCAL_EXECUTION** — authorize only the local dry-run scope below, still subject to remaining gates.
2. **DENY** — refuse controlled activation; keep LOCKED / NO.
3. **RETURN_FOR_CHANGES** — reject the request as packaged; require rework before re-review.

---

## Exact authorization boundary

| Field | Value |
|--------|--------|
| Candidate ID | `HELM-H1-CANDIDATE-20260712T013903Z-4B7F62BE` |
| Package ID | `HELM-H1-CANDIDATE-20260712T013903Z-4B7F62BE` |
| Package digest | `97910a44dbc757d2f5c84a00812976686bcff4456bfba5c0c912ad2f242f819f` |
| Implementation commit | `b39c196e5470857a7b8c713de124f6e73b0a7694` |
| Requested execution scope | `h1c_controlled_dry_run`, `local_read_only_probe`, `local_ledger_write`, `local_evidence_emit` |
| Environment | `local_only` |
| Duration | 600 seconds (requested); authorization must carry an explicit `expires_at` when granted |
| Expiration policy | Time-limited; expired grants fail closed and cannot execute |
| External dispatch | **false** (prohibited) |
| Founder-only actions (spend/sign/submit/keys) | **false** (prohibited in this scope) |
| Automatic relock | **required** after completion or failure |
| Operator-hold release | **required** via governed lifecycle (not file delete) |
| Fresh non-mock live proof | **required** before `safe_to_execute=YES` |

---

## What approval would permit

Only the **specific local, non-destructive dry-run scope** encoded in the packet:

- local read-only probes;
- local ledger writes under H1C ledgers;
- local evidence emit under the H1C evidence tree;
- H1C controlled dry-run mission kind.

Approval does **not** start execution by itself.

---

## What approval would not permit

Explicitly excluded even if APPROVE is recorded:

- production deployment;
- external network dispatch;
- spending / money movement;
- key provisioning;
- code signing;
- store or release submission;
- cloud-resource creation;
- modification of production infrastructure;
- authorization of any **other** candidate, package, digest, or commit.

---

## Remaining gates after approval

Approval alone must **not** start execution. Still required:

1. Valid governed operator-hold release (ledgered; attributable; fresh).
2. Fresh non-mock live proof.
3. Exact candidate and package digest match.
4. Authorization scope match (no widening).
5. Authorization not expired, revoked, or superseded.
6. Final runtime state showing `safe_to_execute=YES` only when all of the above hold.
7. Automatic relock after completion or failure.

---

## Risks

- **Stale or forged live proof** presented as fresh.
- **Scope expansion** beyond the packet after grant.
- **Digest mismatch** (package mutated after review).
- **Stale backend process** serving old code after grant.
- **Operator-hold bypass** (delete hold file without ledgered release).
- **Failure to relock** after mission completion/failure.
- **Accidental external dispatch** if environment constraints regress.
- **Evidence mutation** after authorization (hashes diverge from packet).

---

## Recommendation

**Recommend APPROVE_CONTROLLED_LOCAL_EXECUTION only if** Michael confirms that all requested scope is:

- strictly **local**;
- **non-destructive**;
- **non-external** (no network dispatch);
- **time-limited** with an explicit expiry when signed;
- **digest-bound** to package `97910a44…` and commit `b39c196e…`;
- subject to **automatic relock**.

Do **not** recommend unrestricted execution, production promotion, or clearing operational blockers by hand.

If any of the above is unclear, choose **RETURN_FOR_CHANGES** or **DENY**.

---

## Current runtime (at packet generation)

- `promotion=LOCKED`
- `safe_to_execute=NO`
- `authorization_status=NOT_GRANTED`
- Operator hold: ACTIVE
- Live proof: MISSING

Pending unsigned template: `founder_authorization.pending.json` (must remain `PENDING_FOUNDER_DECISION` until Michael decides).
