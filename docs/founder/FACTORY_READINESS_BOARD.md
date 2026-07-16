# HELM Factory Readiness Board

_Generated 2026-07-16T21:46:47Z by `scripts/factory_readiness.py` — read-only (`curl -s` probes only; no writes, no deploys, no Stripe mutations)._

**Rung scale:** 0 IDEA · 1 PROTOTYPE · 2 BUILT_NOT_SELLABLE · 3 PRODUCTIZED_DEFINED_ONLY · 4 SELLABLE (live checkout reachable) · 5 EARNING (a real charge has settled).

| Factory | Product | Src on disk | Home | Checkout | Observed rung | Asserted rung |
|---|---|:--:|:--:|:--:|---|---|
| HSF | HSF_STORY_STUDIO | ❌ | ✅ 200 | ✅ Stripe | 4 SELLABLE | 3_PRODUCTIZED_DEFINED_ONLY ⚠ |
| HCF | HCF_CYBERQRG_AI | ✅ | — | — | 2 BUILT (source on disk) | 3_SELLABLE_READY (staged — built, priced, checkout wired; one founder --go from live) ⚠ |
| HASF | EPIC_FURY_2026 | ❌ | ✅ 200 | ◐ page | 4 SELLABLE (page-based checkout; Stripe-URL probe N/A) | 4_SELLABLE |
| HFF | HFF_RUNWAY_PACKET | ❌ | — | — | 1 IDEA/DEFINED ONLY | 3_PRODUCTIZED_DEFINED_ONLY ⚠ |
| HMF | HMF_CUE_LIBRARY | ❌ | — | — | 1 IDEA/DEFINED ONLY | 3_PRODUCTIZED_DEFINED_ONLY ⚠ |
| HRF | HRF_CLARITY_BRIEFS | ❌ | — | — | 1 IDEA/DEFINED ONLY | 2_BUILT_NOT_SELLABLE ⚠ |

⚠ = observed rung differs from the rung asserted in the manifest — reconcile.

## Per-product read (evidence)

### HSF_STORY_STUDIO — Story Studio — One-Story Export ($19 one-time) + Creators ($12/mo)
- **Factory:** HSF
- **Source on disk:** NO — declared UNKNOWN / NOT-IN-REPO / clobber-guarded
- **Live URL:** https://story-studio-live.vercel.app
- **Homepage:** HTTP 200 (200 OK)
- **Checkout probe:** returns real Stripe checkout URL
- **Stripe account wired:** yes; **prices declared:** yes
- **Observed rung:** 4 (SELLABLE) · **Manifest asserts:** 3_PRODUCTIZED_DEFINED_ONLY

### HCF_CYBERQRG_AI — CyberQRG-AI — QR safety scanner
- **Factory:** HCF
- **Source on disk:** yes — products/cyberqrg-ai/deploy
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** yes
- **Observed rung:** 2 (BUILT (source on disk)) · **Manifest asserts:** 3_SELLABLE_READY (staged — built, priced, checkout wired; one founder --go from live)

### EPIC_FURY_2026 — Epic Fury 2026 — Conflict-intelligence platform
- **Factory:** HASF
- **Source on disk:** NO — declared UNKNOWN / NOT-IN-REPO / clobber-guarded
- **Live URL:** https://epic-fury-2026.vercel.app
- **Homepage:** HTTP 200 (200 OK)
- **Checkout probe:** POST /api/create-checkout-session -> 404; page-based checkout https://epic-fury-2026.vercel.app/upgrade -> 200 (not a POST-Stripe-session model; Stripe-URL probe N/A)
- **Stripe account wired:** yes; **prices declared:** yes
- **Observed rung:** 4 (SELLABLE (page-based checkout; Stripe-URL probe N/A)) · **Manifest asserts:** 4_SELLABLE

### HFF_RUNWAY_PACKET — Runway — Monthly Cash-Flow & Tax-Prep Packet
- **Factory:** HFF
- **Source on disk:** NO — path not present on disk
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** no
- **Observed rung:** 1 (IDEA/DEFINED ONLY) · **Manifest asserts:** 3_PRODUCTIZED_DEFINED_ONLY

### HMF_CUE_LIBRARY — HOCH Cue Library — Cleared Instrumental Cues for Creators
- **Factory:** HMF
- **Source on disk:** NO — path not present on disk
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** no
- **Observed rung:** 1 (IDEA/DEFINED ONLY) · **Manifest asserts:** 3_PRODUCTIZED_DEFINED_ONLY

### HRF_CLARITY_BRIEFS — Clarity Briefs — cited plain-English research digests
- **Factory:** HRF
- **Source on disk:** NO — declared UNKNOWN / NOT-IN-REPO / clobber-guarded
- **Live URL:** (none declared)
- **Stripe account wired:** no; **prices declared:** no
- **Observed rung:** 1 (IDEA/DEFINED ONLY) · **Manifest asserts:** 2_BUILT_NOT_SELLABLE

## Recommended NEXT-BEST candidate

_The pipeline `scripts/factory_to_money.sh --go` **fails closed** unless the product's source is verifiably on disk (the source-match guard). So the next-best candidate is the one the pipeline can actually advance NOW — source present, not yet sellable — not merely the one that looks most 'live'._

**➡ HCF_CYBERQRG_AI** (HCF) — readiness score 60/100, observed rung 2 (BUILT (source on disk)). Source is ON DISK (`products/cyberqrg-ai/deploy`), so the source-match guard will PASS.

Remaining to reach rung-4 SELLABLE: wire a live Stripe key into the per-product Keychain (one-time paste); first deploy via the guarded pipeline; idempotently create/reuse its Stripe price + set Vercel env + smoke-test checkout. `factory_to_money.sh` does all of this, gated behind the founder's `--go` + Vercel sign-in.

    cd products/cyberqrg-ai/deploy && scripts/factory_to_money.sh HCF_CYBERQRG_AI --plan
    # then, when the source guard passes and founder is signed into Vercel:
    scripts/factory_to_money.sh HCF_CYBERQRG_AI --go

### Already SELLABLE (advance to EARNING, rung 5)
- **HSF_STORY_STUDIO** — checkout returns a real Stripe URL; first *settled* charge confirms rung 5 (NO FAKE GREEN: not earning until the balance txn settles).
- **EPIC_FURY_2026** — page-based checkout live; first *settled* charge confirms rung 5 (NO FAKE GREEN: not earning until the balance txn settles).

