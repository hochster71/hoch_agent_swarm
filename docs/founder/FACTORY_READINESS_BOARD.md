# HELM Factory Readiness Board

_Generated 2026-07-17T13:00:08Z by `scripts/factory_readiness.py` — read-only (`curl -s` probes only; no writes, no deploys, no Stripe mutations)._

**Rung scale:** 0 IDEA · 1 PROTOTYPE · 2 BUILT_NOT_SELLABLE · 3 PRODUCTIZED_DEFINED_ONLY · 4 SELLABLE (live checkout reachable) · 5 EARNING (a real charge has settled).

> NOTE: run with `--no-net` — homepage/checkout columns were NOT probed this run.

| Factory | Product | Src on disk | Home | Checkout | Observed rung | Asserted rung |
|---|---|:--:|:--:|:--:|---|---|
| HCF | HCF_CYBERQRG_AI | ✅ | — | — | 2 BUILT (source on disk) | 3_SELLABLE_READY (staged — built, priced, checkout wired; one founder --go from live) ⚠ |
| HFF | HFF_RUNWAY_PACKET | ✅ | — | — | 2 BUILT (source on disk) | 2_BUILT_NOT_SELLABLE |
| HMF | HMF_CUE_LIBRARY | ✅ | — | — | 2 BUILT (source on disk) | 2_BUILT_NOT_SELLABLE |
| HRF | HRF_CLARITY_BRIEFS | ✅ | — | — | 2 BUILT (source on disk) | 2_BUILT_NOT_SELLABLE |
| HASF | EPIC_FURY_2026 | ❌ | ❌ — | ❌ — | 3 DEFINED (priced, nothing live) | 4_SELLABLE ⚠ |
| HSF | HSF_STORY_STUDIO | ❌ | ❌ — | ❌ — | 3 DEFINED (priced, nothing live) | 3_PRODUCTIZED_DEFINED_ONLY |

⚠ = observed rung differs from the rung asserted in the manifest — reconcile.

## Per-product read (evidence)

### HCF_CYBERQRG_AI — CyberQRG-AI — QR safety scanner
- **Factory:** HCF
- **Source on disk:** yes — products/cyberqrg-ai/deploy
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** yes
- **Observed rung:** 2 (BUILT (source on disk)) · **Manifest asserts:** 3_SELLABLE_READY (staged — built, priced, checkout wired; one founder --go from live)

### HFF_RUNWAY_PACKET — Runway — Monthly Cash-Flow & Tax-Prep Packet
- **Factory:** HFF
- **Source on disk:** yes — products/hff-runway
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** no
- **Observed rung:** 2 (BUILT (source on disk)) · **Manifest asserts:** 2_BUILT_NOT_SELLABLE

### HMF_CUE_LIBRARY — HOCH Cue Library — Cleared Instrumental Cues for Creators
- **Factory:** HMF
- **Source on disk:** yes — products/hmf-cue-library
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** no
- **Observed rung:** 2 (BUILT (source on disk)) · **Manifest asserts:** 2_BUILT_NOT_SELLABLE

### HRF_CLARITY_BRIEFS — Clarity Briefs — cited plain-English research digests
- **Factory:** HRF
- **Source on disk:** yes — products/hrf-clarity-briefs
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** no
- **Observed rung:** 2 (BUILT (source on disk)) · **Manifest asserts:** 2_BUILT_NOT_SELLABLE

### EPIC_FURY_2026 — Epic Fury 2026 — Conflict-intelligence platform
- **Factory:** HASF
- **Source on disk:** NO — declared UNKNOWN / NOT-IN-REPO / clobber-guarded
- **Live URL:** https://epic-fury-2026.vercel.app
- **Homepage:** HTTP —
- **Checkout probe:** network checks skipped (--no-net)
- **Stripe account wired:** yes; **prices declared:** yes
- **Observed rung:** 3 (DEFINED (priced, nothing live)) · **Manifest asserts:** 4_SELLABLE

### HSF_STORY_STUDIO — Story Studio — One-Story Export ($19 one-time) + Creators ($12/mo)
- **Factory:** HSF
- **Source on disk:** NO — declared UNKNOWN / NOT-IN-REPO / clobber-guarded
- **Live URL:** https://story-studio-live.vercel.app
- **Homepage:** HTTP —
- **Checkout probe:** network checks skipped (--no-net)
- **Stripe account wired:** yes; **prices declared:** yes
- **Observed rung:** 3 (DEFINED (priced, nothing live)) · **Manifest asserts:** 3_PRODUCTIZED_DEFINED_ONLY

## Recommended NEXT-BEST candidate

_The pipeline `scripts/factory_to_money.sh --go` **fails closed** unless the product's source is verifiably on disk (the source-match guard). So the next-best candidate is the one the pipeline can actually advance NOW — source present, not yet sellable — not merely the one that looks most 'live'._

**➡ HCF_CYBERQRG_AI** (HCF) — readiness score 60/100, observed rung 2 (BUILT (source on disk)). Source is ON DISK (`products/cyberqrg-ai/deploy`), so the source-match guard will PASS.

Remaining to reach rung-4 SELLABLE: wire a live Stripe key into the per-product Keychain (one-time paste); first deploy via the guarded pipeline; idempotently create/reuse its Stripe price + set Vercel env + smoke-test checkout. `factory_to_money.sh` does all of this, gated behind the founder's `--go` + Vercel sign-in.

    cd products/cyberqrg-ai/deploy && scripts/factory_to_money.sh HCF_CYBERQRG_AI --plan
    # then, when the source guard passes and founder is signed into Vercel:
    scripts/factory_to_money.sh HCF_CYBERQRG_AI --go

