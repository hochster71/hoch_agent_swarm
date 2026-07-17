# HFF Product — "Runway" (Monthly Cash-Flow & Tax-Prep Packet)

**Factory:** HFF · Hoch Finance Factory · *Budgeting · Cash-flow · Tax packet (no advice)*
**Registry:** `coordination/products/product_registry.json` → `HFF_RUNWAY_PACKET`
**Rung today:** 3 · PRODUCTIZED (defined only) — no artifact yet, no checkout, $0 earned.
**Status:** first-mission spec STAGED. Do **not** dispatch during the active soak (seeding live missions corrupts the 24/7 proof). Dispatch after seal.

## Product

Automated monthly packet for solo operators who have no bookkeeper:

- 30/60/90-day cash-flow snapshot (inflows/outflows, runway in months)
- categorized transaction rollup (from a CSV/bank export the user supplies)
- estimated quarterly-tax worksheet (federal + SE tax math shown, inputs labeled)
- year-end 1099-candidate list (contractors paid > $600, missing-W-9 flags)
- one clean PDF/XLSX handoff for the user's own CPA

**Price:** $15/mo ($150/yr). **Buyer:** solo founders, freelancers, single-member LLCs.

**Hard guardrail:** organizational tooling ONLY — never financial, investment, or tax *advice*. Every output carries a "prepared for your accountant; not advice" banner. This mirrors the existing tax-prep skill doctrine already in the repo.

## First mission (dispatch after soak seals)

> **Goal:** produce HFF's first validated artifact — a real "Runway" packet from a sample transaction CSV — so the factory moves DECLARED → PRODUCES.

- **Input:** a synthetic/sample transactions CSV (no real founder financial data).
- **Output artifact:** `runway_packet_<UTC>.xlsx` + a one-page PDF summary, written under `docs/scratch/artifacts/` and validated (schema + math checks).
- **Acceptance:** cash-flow totals reconcile to the CSV; estimated-tax worksheet arithmetic verified programmatically; 1099 list matches the >$600 rule; advice-language linter finds zero advice phrases.
- **Definition of done for this rung:** one validated artifact exists → census shows HFF at PRODUCES (2), not DECLARED (0).

## Path to first dollar (later, founder-gated at the checkout step)

PRODUCES → PRODUCTIZED (done: name+price) → **SELLABLE** (needs a real checkout: Stripe product + payment link — founder-gated) → EARNING (a stranger pays). No checkout is built yet; that step stops at the founder door.
