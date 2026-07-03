# main.py Decomposition Plan (H4)

## Finding
`backend/main.py` is ~12,095 lines with 365 route handlers. Every gate,
authority, and ledger endpoint lives in one file — a single bad merge can
silently drop a control. This is a maintainability + security-review risk.

## Why not split it all at once
A big-bang extraction of 50+ endpoints from a 12k-line module mid-security-
remediation is itself risky: shared module-level state (`app`, DB helpers,
`TEST_MODE`, in-memory caches) and import cycles make it error-prone. The
codebase already uses `app.include_router(...)` for `michael_ai`, `goal`, and
`qa`, so the target pattern is proven — we migrate incrementally.

## Interim guard (in place now)
`tests/unit/test_security_endpoint_inventory.py`:
- pins the security-critical routes so their removal fails CI,
- asserts founder-signature enforcement strings are still present,
- caps main.py at 12,500 lines (ratchet DOWN after each extraction; never up).

## Migration order (extract into `backend/routers/`)
Each step: move handlers + their Pydantic models into a router module, replace
`@app.` with `@router.`, add `app.include_router(router)`, run full suite.

1. `routers/release_authority.py` — `/api/v1/release/authority/*`,
   `/api/v1/release/promote`, `/api/v1/release/signing-*`. (Highest security
   value; smallest blast radius.)
2. `routers/approvals.py` — `/api/v1/approvals/*`, `/api/approval/*`.
3. `routers/security_ops.py` — `/api/v1/security-ops/*`, `/api/security/*`.
4. `routers/release_evidence.py` — `/api/v1/release/evidence/*`,
   attestation/seal endpoints.
5. Remaining domain routers (pods, devices, models, prompts, toolops…).

After each step, lower the line ceiling in the guard test to the new count.

## Definition of done
`main.py` retains only app setup, middleware, shared dependencies, and
`include_router` calls (< ~800 lines).
