# HOCH — Cross-Factory Gap Analysis

*Evidence-grounded: gene/quantity numbers come from `gap_analysis.py` run live across all three
domains; milestone gaps from each factory's PERT doc; no fake-green.*

## 1. Quantity gaps (gene pools) — from the live engine

| Factory | genes | classes | thin | genes needed | champions | state |
|---|---|---|---|---|---|---|
| **HASF** (software) | 479 | 30 | **0** ✅ | 0 | 26 | IMPROVING |
| **HMF** (music) | 10 | 8 | 8 | 14 | 0 | SEEDED |
| **HRF** (research) | 8 | 7 | 7 | 13 | 0 | SEEDED |

**HASF milestone reached:** the EXPAND lever grew the pool 427 → 479 (+52, the exact predicted
deficit) and drove thin classes 15 → 0. Quantity is no longer the binding constraint on HASF.
**HMF + HRF** are freshly seeded — their thin domains are expected (M1 not yet run). Total synthetic
genes to fill every thin class across HOCH: **27** ($0, local model).

## 2. Milestone gaps to each GOAL

| Factory | at | next $0 gap | frontier / cost gap |
|---|---|---|---|
| HASF | production-adjacent, signed GO | keep improving; ship a revenue product | Rung-2 judge (paid) |
| HMF | M0 scaffold | M1 expand + **crown champions** | M2 render, M3 audio judge (cost) |
| HRF | M0 + **M2/M3 proven live** (grounding + citation verify) | M1 expand + **crown champions** | M4 execution, M5 novelty judge |

## 3. Cross-cutting HOCH platform gaps (the real list)

1. **HMF & HRF have 0 champions.** The seeds exist but no champion has been crowned per domain,
   so both read SEEDED with no mean score. **Cause:** `run_m0` (selection/convergence) is still
   software-only — it uses the software scorer + flat paths. **Fix:** a domain-aware selection pass
   that crowns a champion per class using each factory's own scorer. $0, mechanical, immediate.
2. **The cadence only drives software.** `brain_cadence.sh` + the meta-loop run the software domain;
   HMF/HRF don't get automatic cycles. **Fix:** loop the cadence over all registered factories.
3. **Domain generators/judges are the frontier gaps** (known, not silent): HMF render + audio judge,
   HRF computational execution + novelty judge. These are the cost/Rung-2 decisions.
4. **Console — CLOSED just now:** it renders all three factories from the live feed. ✅
5. **HRF citation gate — CLOSED:** covers DOI + PMID + arXiv, fail-closed, proven live. ✅

## 4. Highest-leverage next move ($0)

**Close gap #1 + #2 together:** make `run_m0` domain-aware and loop the cadence over all factories.
Result: HMF and HRF go from SEEDED (0 champions) to having real champions + a live mean score from
their own seed pools — every factory becomes a *live* node on the console, honestly scored. Then M1
expansion (also $0, local model) grows the thin domains.

Frontier gaps (HMF render/judge, HRF execution/judge) stay explicitly deferred as cost decisions —
no fake-green: those factories will read "champions from seeds," not "production-ready."
