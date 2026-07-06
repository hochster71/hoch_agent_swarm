# HOCH — Multi-Factory Architecture

**HOCH** is the umbrella. Under it:

- **HAS** — the *Governor*. Command & control: safety tiers, evidence discipline, the relay mesh,
  autonomy runner (HELM), execution adapters (AG).
- **BRAIN** — the *Mind*. One self-improving cognitive core, now **multi-domain**: it holds a
  separate gene pool + convergence state per Factory domain, but runs the *same* engine
  (harvest → splits → gap-analysis → gene-expansion → best-of-N → honest-convergence → meta-loop).
- **The Factories** — the *Makers*. Each turns BRAIN-optimized genes + domain tooling into the best
  output in its medium, under HAS governance:
  - **HASF** — Hoch Application Software Factory (software/apps)
  - **HMF** — Hoch Music Factory (digital music, every genre)
  - future, same `H_F` convention: **HWF** (Writing), **HVF** (Video), **HIF** (Image/Art),
    **HGF** (Games), **HDF** (Design)

```
                ┌──────────────── HAS · Governor ─────────────────┐
                │  safety tiers · evidence discipline · relay · AG  │
                └───────────────────────┬──────────────────────────┘
                                        │ governs
                ┌──────────────── BRAIN · Mind (multi-domain) ─────┐
                │  per-domain: gene pool · convergence · gaps · meta│
                └──┬───────────────┬───────────────┬───────────────┘
              software           music           writing  ...
             ┌────▼────┐     ┌─────▼────┐    ┌──────▼────┐
             │  HASF   │     │   HMF    │    │   HWF     │   ← the Makers
             └─────────┘     └──────────┘    └───────────┘
```

## The Factory contract

Adding a Factory is *declaring four things*, not rewriting the engine. Every Factory instance
provides:

| Field | What it is | HASF | HMF |
|---|---|---|---|
| `domain` | state namespace | `software` | `music` |
| `rubric` | dimensions + weights the scorer measures | discipline rubric | music rubric |
| `scorer` | mechanical PROXY → 0–100 (labeled, not a quality verdict) | `scorer.py` | `music_scorer.py` |
| `generator` | creates candidate genes ($0 local model) | LLM prompt-writer | music recipe / model |
| `judge` | quality veto (anti-Goodhart) | LLM-as-judge | audio judge / human A-B |
| `gates` | pre-publish approvals | tests, audit | **originality + licensing + T3 publish** |

The domain-agnostic engine already takes *paths + rubric*, so HASF and HMF share:
`harvest`, `splits`, `gap_analysis`, `gene_expansion`, `improve_loop` (best-of-N), `convergence`
(honest guard), `research_meta`. **Music reuses all of it.** Only `scorer`, `generator`, `judge`,
and `gates` are domain-specific.

## Multi-domain BRAIN layout (backward compatible)

```
data/prompt_brain/                 ← software domain stays flat (existing, unbroken)
  gene_pool_m0.json
  champion_registry.json
  convergence_status.json
data/prompt_brain/music/           ← new domains are subfolders
  gene_pool.json
  champion_registry.json
  convergence_status.json
```

The **software** Factory keeps its current flat paths (nothing moves, nothing breaks). New domains
get a subfolder. The Factory registry maps each `domain → paths + rubric + scorer`.

## What HMF forces that HASF did not (honest constraints)

1. **Quality can't be keyword-scored.** The software mechanical proxy reads discipline *keywords*;
   music can't be judged that way. `music_scorer` scores **recipe completeness** (a genuine proxy
   for whether a track spec is production-ready) and is explicitly labeled `MECHANICAL_PROXY` — it
   is **not** a claim the music sounds good. The real verdict needs an audio judge or a human A/B.
   At $0 with a local model, that judge is the weak link → HMF leans on human A/B longer than HASF.
   No fake-green: a track is never "great" without a real listen or measurement.
2. **Originality is a governance gate.** HAS must enforce: never clone a real, named artist's
   work or voice; run a similarity/sampling check before anything is published. New HAS duty.
3. **Publishing + monetization is T3.** Distribution (DistroKid/Spotify/Apple Music), royalties,
   and spend are money-and-publish tier — operator approval required, same as every other T3 action.

## Naming summary

| Layer | Name | Role |
|---|---|---|
| Umbrella | **HOCH** | the whole system |
| Governance | **HAS** | the Governor |
| Cognition | **BRAIN** | the Mind (multi-domain) |
| Production | **the Factories** | the Makers — HASF, HMF, HWF, HVF, HIF, HGF, HDF |

**One Governor. One Mind. Many Makers.**
