# HRF Clarity Briefs — Engine Build Spec

**Product:** `HRF_CLARITY_BRIEFS` — "Clarity Briefs: cited plain-English research digests"
**Factory:** HRF · Hoch Research Factory
**Today's real state:** checkout scaffold only (`products/hrf-clarity-briefs/` — landing + `api/create-checkout-session.js`, fail-safe 501). **There is no generator.** A buyer would pay and get nothing. This spec defines the engine that turns the shell into a real product.
**Rung:** 2 → target 4 (sellable) once the engine produces a validated, cited brief on demand.

---

## What to build

A **research → cited-brief generator**: given a topic/question, it produces a plain-English brief where **every factual claim carries an inline citation to a real, retrievable source**, plus an explicit **"What we're unsure about"** uncertainty section. The honesty discipline — a claim without a source does not ship — is the entire value proposition and the anti-slop moat.

**Pipeline (5 stages):**
1. **Intake** — user submits a question + optional scope (recency window, depth). Validate/normalize.
2. **Retrieve** — real web/literature search (NOT the simulated `scripts/dispatch_research.py`, which is theater). Use the live `WebSearch` / `web_fetch` tool path and, for scientific topics, the connected research MCPs already in this environment (PubMed, bioRxiv, Consensus, ClinicalTrials). Collect candidate sources with URL + title + retrieved-at timestamp.
3. **Extract & attribute** — for each source, pull supporting passages; bind each to the specific claim it supports. Drop any claim with zero surviving support (fail-closed).
4. **Compose** — draft the brief; enforce **citation-per-claim** (every declarative sentence in the findings maps to ≥1 source id). Generate the **uncertainty section** from: claims that had thin/single-source support, conflicting sources, and gaps where retrieval found nothing.
5. **Verify & render** — run the citation-coverage linter (below); render to HTML + PDF with a numbered reference list of live links.

## Inputs / Outputs

- **Input:** `{ question: string, recency_days?: int, depth?: "brief"|"deep", domains?: string[] }`
- **Output:** `brief_<slug>_<UTC>.pdf` + `.html` + a `brief.json` sidecar: `{ claims: [{text, citations:[{source_id,url,title,quote}]}], uncertainty: [...], sources: [...], coverage_pct }`.
- **Hard invariant:** `coverage_pct == 100` (every findings claim cited) or the brief does not render — it fails closed with the uncited claims listed.

## Reuse from this repo

- **Checkout shell:** `products/hrf-clarity-briefs/` (already built) + the proven `products/cyberqrg-ai/deploy` Vercel + serverless checkout pattern.
- **Multi-model review/critique:** `backend/coding_control_plane/reviewer_council.py` + `scripts/claude_critic_adapter.py` + the `scripts/council/` dir — repurpose the council-of-critics pattern to fact-check the draft against its own cited quotes (a second pass that asks "does this quote actually support this claim?").
- **Live retrieval:** the `WebSearch` / `web_fetch` tools and the connected bio/research MCPs (PubMed, bioRxiv, Consensus, ClinicalTrials) — real sources, no fabrication.
- **Rendering:** the `anthropic-skills:pdf` skill (or `docx`) for the PDF/HTML handoff.

## Guardrail

**No claim without a live, retrievable citation. No fabricated sources, quotes, or URLs.** Every citation must be a real URL fetched during the run (retrieved-at timestamp stored). The uncertainty section is mandatory, never empty-by-omission — if the model is confident on everything, the linter must still force an explicit "limits of this brief" note. This is a *research digest*, not authoritative advice; brief carries a "synthesized from cited public sources; verify before acting" banner.

## Definition of done (shell → sellable)

- A stranger submits a real question and receives a brief where **100% of findings claims resolve to a working citation link**, verified by the coverage linter (fails the build otherwise).
- The uncertainty section is present and non-trivial on ≥3 diverse test topics.
- The council fact-check pass runs and flags at least the seeded "unsupported claim" test case (proves the check is real, not decorative).
- End-to-end latency and cost are bounded and logged per brief.

## Honest effort estimate

**The largest of the three.** The checkout is done; the engine is ~all of the work. Retrieval + attribution + the citation-coverage linter + a fact-check pass is a real multi-day build (call it a solid week to a trustworthy v1), because the moat *is* rigor — a plausible-but-unverified brief is worse than nothing. The council/critic and retrieval plumbing already exist to lean on, which is the main accelerant.
