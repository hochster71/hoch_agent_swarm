# HFF Runway — Engine Build Spec

**Product:** `HFF_RUNWAY_PACKET` — "Runway: Monthly Cash-Flow & Tax-Prep Packet" ($15/mo, $150/yr)
**Factory:** HFF · Hoch Finance Factory
**Today's real state:** checkout scaffold only (`products/hff-runway/` — landing + `api/create-checkout-session.js`, fail-safe 501) + a mission spec (`docs/factories/products/HFF_runway.md`). **There is no packet generator.** This spec defines the engine.
**Rung:** 3 (defined) → target 4 (sellable) once the engine turns a real bank CSV into a validated packet.

---

## What to build

A **bank-CSV → cash-flow / tax-prep packet generator**. The buyer (a solo operator with no bookkeeper) uploads a CSV/bank export; the engine returns one clean packet their CPA can work from. This is **organizational tooling that shows the math with labeled inputs — never advice.**

**Pipeline (5 stages):**
1. **Ingest & normalize** — accept common CSV shapes (date, description, amount, optional category). Auto-detect columns; normalize signs (inflow/outflow); handle multiple accounts. Reject/flag unparseable rows rather than silently dropping them.
2. **Categorize** — rules-based categorization (keyword → category map, user-overridable), producing a categorized transaction rollup. Deterministic and auditable — no black-box guessing on money.
3. **Cash-flow** — 30/60/90-day inflow/outflow snapshot + runway-in-months (cash ÷ avg monthly burn).
4. **Tax-prep worksheets** — estimated quarterly-tax worksheet (federal + SE tax **arithmetic shown, every input labeled**) and a year-end **1099-candidate list** (contractors paid > $600, missing-W-9 flags). All numbers are computed and shown, framed as "for your accountant."
5. **Render & validate** — emit `runway_packet_<UTC>.xlsx` (tabbed: transactions, categories, cash-flow, est-tax, 1099) + a one-page PDF summary. Run the validation suite before release.

## Inputs / Outputs

- **Input:** a transactions CSV (columns auto-mapped), + minimal profile: `{ filing_type, state?, period }`. **No live bank connection in v1** — the user supplies the export (smaller blast radius, no credential handling).
- **Output:** `runway_packet_<UTC>.xlsx` + one-page `.pdf` summary. Every sheet carries the non-advice banner.

## Reuse from this repo

- **Checkout shell:** `products/hff-runway/` (already built) + the `products/cyberqrg-ai/deploy` Vercel + serverless checkout pattern.
- **Spreadsheet / PDF output:** the `anthropic-skills:xlsx` skill for the multi-tab workbook and `anthropic-skills:pdf` for the summary — these are the exact deliverable formats the mission spec calls for.
- **Advice-language linter:** `docs/factories/products/HFF_runway.md` already mandates an "advice-phrase linter (finds zero advice phrases)." Build it as a small deterministic checker (banned-phrase list: "you should invest", "we recommend", "the best move is", tax *strategy* verbs, etc.) run over every rendered string — reuse the same fail-closed gate pattern as the repo's other content gates (e.g. `scripts/anti_fake_gate.sh`).
- **Validation harness:** mirror the mission spec's acceptance checks (totals reconcile to CSV, est-tax arithmetic verified programmatically, 1099 list matches the >$600 rule).

## Guardrail (HARD)

**Organizational tooling ONLY — never financial, investment, or tax *advice*.** The engine computes, categorizes, and shows math with labeled inputs; it does not tell the user what to do. Every output sheet and the PDF carry a visible **"Prepared for your accountant. Not financial or tax advice."** banner. The advice-language linter runs on every release and **fails the packet closed** if any advice phrase is detected. No live bank credentials are touched in v1.

## Definition of done (shell → sellable)

- A stranger uploads a real (or realistic) transactions CSV and gets back a packet where: cash-flow totals **reconcile exactly to the CSV**; the estimated-tax worksheet arithmetic is **programmatically verified**; the 1099 list **matches the >$600 rule**; and the **advice-language linter finds zero advice phrases** (fails the build otherwise).
- Runs on ≥3 differently-shaped sample CSVs without manual fixups.
- The non-advice banner is present on every rendered artifact.

## Honest effort estimate

**The most tractable of the three** — it's deterministic data transformation, not open-ended generation, and the xlsx/pdf skills do the heavy rendering. The real work is robust CSV ingestion (messy real-world exports), the categorization rule set, and getting the SE/estimated-tax arithmetic correct and clearly labeled. A focused few days to a validated v1. The guardrail (advice linter) is cheap to build and non-negotiable.
