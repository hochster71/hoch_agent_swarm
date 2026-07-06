# BRAIN Acceleration — Audit, Gap Analysis, and the Self-Directing Loop

**Goal:** accelerate intelligence by improving prompt *quality* and expanding prompt *quantity*
across all areas, close the gaps, run the loop more frequently, and keep going until the brain
honestly can't get smarter — with **no fake-green** at any step.

## Audit (ground truth at gen 10)

| metric | value |
|---|---|
| mean champion score | 60.77 (from 50.77 at gen 1) |
| champions | 26 |
| gene pool | 427 genes / 30 classes |
| pool concentration | top-5 classes hold 68% of genes |
| real improvements to date | 6 (Audit, SAST, Vuln Mgmt, Detection Eng, Data Security, Governance) |

## Binding constraints (from `gap_analysis.py`, recomputed every cycle)

| constraint | count | meaning | lever |
|---|---|---|---|
| THIN_POOL | 15 | ≤5 genes — champion has no competition, quantity-capped | **EXPAND** |
| LOW_CEILING | 10 | adequate pool, champion below target 70 | **IMPROVE** (best-of-N) |
| SATURATED | 5 | at/above target for now | hold |

- **52 synthetic genes** needed to bring every thin class to `min_pool=6`.
- The lowest champions (AI/ML Systems 40, Coding 45, Supply Chain 45, Privacy 47.5) are exactly the
  thin-pool classes — **quantity is the binding constraint on quality.**
- Taxonomy drift (merge candidates): `AI/ML ⇄ AI/ML Systems`, `Governance/Compliance ⇄ Governance`,
  `SDLC Governance ⇄ Governance`.

## What was built (all $0, local model; each gate unit-tested)

1. **`gap_analysis.py`** — the audit, codified and repeatable. Per-class binding-constraint
   classifier + taxonomy-drift detector. Writes `gap_analysis.json` (console-readable) + report MD.
2. **`gene_expansion.py`** — the **quantity** lever. Local model synthesizes new genes for thin
   classes; a candidate is admitted only if (a) not a duplicate, (b) mechanical ≥ class median, and
   (c) an LLM judge prefers it over the class's weakest gene. Anti-Goodhart: keyword-stuffing scores
   high mechanically but is judge-vetoed. Every admitted gene labeled `SYNTHETIC_ADMITTED`.
3. **Best-of-N `improve_loop`** — evaluates *all* candidates through the dual gate and keeps the
   strongest judge-approved one (no first-past-the-post bias).
4. **Coverage-aware `improve_run`** — half the budget to the weakest champions, half rotating through
   *all* classes via a persisted cursor, so every area is worked over successive cycles.
5. **Honest-convergence guard (`convergence.py`)** — a no-gain generation counts toward convergence
   **only if the improver was online**. Blind-flat ⇒ `STALLED_NO_IMPROVER`, never `CONVERGED`. This
   is the only thing that makes "until we can't get smarter" a truthful claim.
6. **Research meta-loop (`research_meta.py`)** — reads the gaps each cycle and picks the single
   highest-leverage lever: `EXPAND → SELECT → IMPROVE → RECONCILE → CONVERGED`. `global_converged`
   is true **only** when online + every class saturated + the mean has plateaued below epsilon.

## The loop (meta-directed cadence, every 10 min)

```
research_meta (pick lever)
  ├─ EXPAND  → expand_run (grow thin pools) → improve_run (best-of-N)
  ├─ IMPROVE → improve_run (best-of-N sweep)
  ├─ SELECT  → mechanical crown
  ├─ RECONCILE → recommend taxonomy merges (operator-confirmed)
  └─ CONVERGED → honest ceiling of current levers
→ run_m0 (select/promote + convergence, passes real improver status)
→ gap_analysis (refresh audit)
→ write_brain_live (publish to the console)
```

Single-flight lock prevents a slow local-model tick from stacking. Interval dropped 30 min → 10 min.

## Honest ceiling ("can't get smarter")

The loop declares `CONVERGED` only when, with the model online: no thin pools remain, every class
has a champion, none are below target, and the mean has plateaued below epsilon for the patience
window. Until then, `global_converged=False`. When the current levers plateau but headroom clearly
remains, the next lever is a **stronger generator** (Rung 2, a frontier model) — a cost decision,
deferred until revenue justifies it. That is the honest boundary of the $0 tier.

## Verification (mechanical pieces, no live model needed)

`tests/integration/test_brain_acceleration.py` — 6 tests: gap thin/drift detection, gene-expansion
dual gate (dedup + median + judge veto), no-backend empties, blind-flat cannot converge, online
plateau does, coverage sweep touches all + prioritizes weakest. Full brain suite: 35 passing.
