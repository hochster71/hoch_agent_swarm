# HMF — GOAL, PERT to Goal, and GO/NO-GO

## The GOAL of HMF (north star)

> **HMF autonomously produces original, production-quality, distribution-ready music across every
> target genre — where every released track carries evidence that it is (1) original and licensed,
> (2) judged good by an audio-quality judge (not just a well-specified recipe), and (3) published
> and monetized under T3 operator approval. No fake-green: a track is never "released-ready" without
> a real listen/measurement behind it.**

The GOAL is *not* "generate audio." It is **evidence-backed, original, publishable music at quality**
— the music analogue of HASF's signed production-readiness.

## Why today is honestly NOT the goal

BRAIN can organize and *score recipes* (M0 done). It cannot yet **render audio**, **judge how audio
sounds**, or **prove originality**. Those are the real work — and the two long poles (render, judge)
are also where the $0 constraint is most at risk. Claiming a production GO now would be fake-green.

## Milestones + evidence gates

| # | Milestone | Evidence gate (what proves it done) | $0? |
|---|---|---|---|
| **M0** | **Factory scaffold** ✅ | registry + music rubric/scorer + seed genes + engine proven domain-agnostic + 9 tests | yes ✅ |
| M1 | Genre coverage / gene expansion | gap_analysis shows no thin genres; every target genre ≥ min_pool; music convergence IMPROVING | yes |
| M2 | Audio render pipeline | reproducible recipe → .wav render, provenance-logged | **cost risk** |
| M3 | Audio-quality judge (anti-Goodhart) | judge separates good/bad renders on held-out; a seeded-bad render is caught | partial |
| M4 | Originality + licensing gate (HAS) | seeded near-copy BLOCKED; clean original PASSES; sample clearance recorded | yes |
| M5 | Distribution + monetization (T3) | one track published to a store under operator approval; ISRC assigned | operator |
| M6 | **Production GO** | M1–M5 evidence chain complete for tracks across genres | — |

## PERT (te = (o + 4m + p) / 6, focused build-days)

| Milestone | o | m | p | **te** | Notes / risk |
|---|---|---|---|---|---|
| M1 genre expansion | 1 | 2 | 5 | **2.3** | $0 now — local model writes recipes, dual-gated |
| M2 render pipeline | 2 | 5 | 12 | **5.7** | frontier; open models (MusicGen/Stable Audio Open) run on your 15-core Mac at $0 but quality-capped; "BEST" may need paid models |
| M3 audio judge | 3 | 7 | 15 | **7.7** | hardest; objective metrics (LUFS/true-peak/spectral/structure) free, semantic "is it a great song" judge is the risk |
| M4 originality gate | 2 | 4 | 8 | **4.3** | can overlap M3 |
| M5 distribution T3 | 1 | 3 | 6 | **3.2** | mostly operator + integration |
| M6 production GO sign | 0.5 | 1 | 2 | **1.1** | evidence-gated signature |

**Critical path M1→M6 ≈ 24.3 build-days** serial; with M4 overlapping M3, **~18–20 build-days**
wall-clock. Calendar depends on your availability (family time is a real constraint). **Variance is
dominated by M2 and M3** — the render + judge frontier is the schedule risk *and* the cost risk.

Critical path: **M2 → M3** are the long poles. Everything else is short or parallelizable.

## The $0 boundary (honest)

- M1, M4: fully $0.
- M2: $0 is *possible* with open local models on your Mac, but "BEST in every genre" quality likely
  needs paid models — a revenue-gated decision, not a blocker to *start*.
- M3: objective audio metrics are $0; a strong semantic judge is the same Rung-2 cost question as HAS.

## GO / NO-GO

- **M0 scaffold — GO (VERIFIED).** Real, tested, engine proven domain-agnostic. Signed below.
- **Production GO (M6) — NO-GO (correctly).** Zero rendered/judged/published tracks exist. Signing
  it would be fake-green. It stays NO-GO until the M1–M5 evidence chain exists.
- **Next action — GO on M1 (genre expansion).** It is $0, available now, and on the critical path.

**Signed:** M0 VERIFIED / M6 NO-GO — pending M1–M5 evidence. Honest state, no fake-green.
