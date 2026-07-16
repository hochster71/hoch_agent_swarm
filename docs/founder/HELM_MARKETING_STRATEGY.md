# HELM Marketing Strategy — LinkedIn + Facebook + light organic (PRODUCTS ONLY)

> Author: HELM swarm agent · 2026-07-16
> Scope: how HELM markets the **products a stranger can buy**. Nothing else.
> Companion docs: `coordination/products/products.json` (source of truth for what's live),
> `docs/founder/epic_fury_first_buyer_kit.md` (the first-buyer kit this doc templatizes).

---

## 0. What this doc is — and what it is explicitly NOT

This is a go-to-market playbook for HELM's **products**: Story Studio, Epic Fury, and the
future pipeline (CyberQRG-AI, Clarity Briefs, Runway, Cue Library). It covers positioning,
who buys, where they gather, the LinkedIn/Facebook/organic channel plan, and a reusable
per-product launch kit.

**Out of scope — do not put any of this in marketing, ever:**
- Michael's personal finances or net worth.
- HELM-internal financials, revenue totals, burn, runway, or the swarm's economics.
- Family / personal life / anything from the personal (HHF) factory.
- Any private info, credentials, account IDs, Stripe/Vercel internals, or infrastructure detail.

Marketing speaks only about **a product a stranger can name, see a price for, and buy.**
If a claim isn't about the product's value to its buyer, it doesn't belong in a post.

---

## 1. THE GOVERNING RULE — the readiness gate (read this first)

**A product is marketed only AFTER its checkout is verified live. Never before.**

The trigger to begin marketing product X is a single, evidence-backed fact:

> **"X's checkout returned a real Stripe Checkout session (or completed a real charge) on evidence."**
> Concretely: X is at **rung 4 (SELLABLE)** or **rung 5 (EARNING)** in `products.json`,
> proven by a live health-check — not a passing mock, not a spec, not a scaffold.

Corollaries (these are the spine — everything below hangs off them):

1. **No dated launch may force product readiness.** We never say "we launch March 1" and then
   scramble to make checkout work by March 1. Readiness pulls marketing, not the reverse.
   The calendar never overrides the gate.
2. **Rung is the only launch signal.**
   - Rung ≤ 3 (idea / built / defined / checkout broken) → **marketing is silent.** Zero posts.
   - Rung 4 (checkout live, real session returned) → **first-buyer kit fires** (§4/§5).
   - Rung 5 (a real charge has **settled** as a balance transaction) → we may say "earning" /
     use social proof of a real sale. Not before settlement (see §7).
3. **A passing test, a green deploy, or a live *preview* page is NOT the gate.** The gate is a
   live *checkout* returning a real session. Free preview working ≠ sellable.
4. **NO FAKE GREEN.** We never imply a product is buyable when its checkout is broken, never
   fabricate demand, sales, reviews, or endorsements, and never attribute a quote to a real
   person who didn't say it.

### Current readiness snapshot (as of 2026-07-16 — re-derive from `products.json` each time)

| Product | Price | Rung | Checkout state | Marketing status |
|---|---|---|---|---|
| **Epic Fury 2026** | $19/mo ($190/yr) | **4 SELLABLE** | Live upgrade page returns session | **CLEARED — run the kit** |
| **Story Studio** | $19 one-time / $12/mo | **3 (NOT sellable)** | Checkout throws `No such price` (Stripe key/price account mismatch) + KV needed | **HOLD — do not market until checkout verified live** |
| CyberQRG-AI | unpriced | 2 | none | HOLD |
| Clarity Briefs | unpriced | 2 | none | HOLD |
| Runway | $15/mo (defined) | 3 | none | HOLD |
| Cue Library | $9/mo (defined) | 3 | none | HOLD |

> Story Studio is a live *preview* but its checkout is broken — under the gate that means
> **silent**. The moment its checkout returns a real session, it graduates to CLEARED and the
> §4 template produces its launch copy the same day.

---

## 2. Per-product positioning (only the live / near-live two)

Honest positioning = the truest sentence a buyer would nod at, with zero overclaim.

### 2a. Epic Fury 2026 — CLEARED (rung 4)
- **What it honestly is:** an OSINT *modeling/simulation* sandbox for the 2026 US–Iran scenario,
  where **every panel is labeled LIVE / SIMULATION / MIXED** so an analyst never mistakes a
  projection for reporting. A thinking tool — **not** a news wire, **not** for operational decisions.
- **One-line positioning:** *"Operator-grade conflict modeling you can actually audit — every
  panel labeled LIVE, SIMULATION, or MIXED, so an analyst never has to guess which they're reading."*
- **Who actually buys at $19/mo:**
  - OSINT / geopolitics analysts.
  - Defense & wargaming hobbyists and professionals.
  - Journalists on the security/defense beat who want a labeled sandbox, not a wire.
  - Analysts burned by "AI predicts the war" hype — the differentiator is the *opposite*:
    transparency + confidence/dissent labeling.
- **Where they already gather:** r/geopolitics, OSINT X/Twitter, Bellingcat-adjacent communities,
  OSINT Discord servers, wargaming subreddits and matrix-game communities, MORS-adjacent groups.
- **Honesty line to never cross:** never remove or weaken LIVE/SIMULATION/MIXED labeling; never
  imply real-time ground truth or decision use. (Full kit: `epic_fury_first_buyer_kit.md`.)

### 2b. Story Studio — ON HOLD (rung 3, checkout broken)
> Positioning is drafted so it's ready the instant the gate opens — but **nothing ships until
> checkout returns a real Stripe session.**
- **What it honestly is:** a tool that turns a few prompts into a finished, shareable animated
  storybook. **One-Story Export** is a $19 one-time unlock of a single finished story;
  **Creators** ($12/mo) is for people who make them repeatedly.
- **Draft one-line positioning:** *"Turn a bedtime idea into a finished, shareable animated
  storybook in minutes — pay only for the one you want to keep."*
- **Who would buy:**
  - $19 one-time: parents and teachers who want *one* finished shareable storybook — no subscription.
  - $12/mo Creators: hobbyist storytellers / repeat makers.
- **Where they gather:** parenting and teacher groups on Facebook, r/Parenting, r/Teachers,
  homeschool communities, kidlit / children's-book maker groups.
- **Do not ship any of this** until the readiness snapshot flips Story Studio to CLEARED.

---

## 3. Channel plan (LinkedIn + Facebook + light organic)

Small budget, founder-led, honesty-first. The point is credible reach into rooms where the
buyer already is — not spray-and-pray, not paid-ad theater.

### 3a. LinkedIn — personal profile is the primary engine
- **Best fit:** Epic Fury (analysts, journalists, defense/risk professionals live here) and
  future B2B-ish products (Runway, Clarity Briefs). Weakest fit for Story Studio (consumer).
- **Personal posts (highest trust):** first-person build-in-public. "I built X because Y bothered
  me. Here's the honest version of what it does and doesn't do. [live link]." Lead with the
  problem and the honesty differentiator, not hype.
- **Company Page (only if one already exists):** mirror the launch post; keep it factual. Do not
  stand up a company page purely to run ads — a founder voice out-converts a logo at this stage.
- **Cadence:** 1 substantive post per live product launch + occasional honest follow-ups
  (a real lesson, a real user question). Don't manufacture a posting streak.
- **Etiquette:** disclose it's your product every time. No fake "look what I found" framing.

### 3b. Facebook — best for consumer products
- **Best fit:** Story Studio (parents/teachers) — **once it's CLEARED.**
- **Personal + relevant Groups:** post in parenting/teacher/homeschool Groups **only where
  self-promo is allowed**, and read each Group's rules first. Contribute value, then share.
- **No dark-pattern targeting; no scraped audiences.** Reach segments where they gather, let
  people opt in.

### 3c. Light organic (low-effort, high-honesty)
- **Reddit / Discord / niche forums:** one honest "I built this, tear it apart" post per relevant
  community, respecting each community's self-promo rule. This is where sharp critique (and early
  buyers) come from.
- **"Show HN"-style intro** for the technical products (Epic Fury).
- **Etiquette that applies everywhere:**
  - Always disclose you're the maker.
  - One post per community, not spam; follow the local rules or don't post.
  - Invite critique, don't demand upvotes.
  - Never fabricate testimonials or reviews. Never buy engagement.

---

## 4. REUSABLE FIRST-BUYER KIT — TEMPLATE (copy for every newly-CLEARED product)

> **When to use:** the moment product X hits rung 4 (checkout returns a real session). Fill the
> brackets, delete the guidance, and X has honest launch copy the same day. Modeled on
> `epic_fury_first_buyer_kit.md`. **Do not use this template while X is rung ≤ 3.**

```
# [PRODUCT NAME] — First-Buyer Kit ([MISSION/ID])

**Gate check (required before this kit ships):** [PRODUCT]'s checkout returned a real Stripe
session on [DATE] — evidence: [health-check result / session id ref]. Rung 4 confirmed.
**Live checkout:** [CHECKOUT URL] · **Price:** [$ / cadence]
**Your only action:** post the landing blurb + send the outreach below. Nothing here spends
money or auto-sends.
**Honesty rule (baked in):** [the one product-specific honesty line that must never be crossed —
e.g. Epic Fury's LIVE/SIMULATION/MIXED labeling; Story Studio's "no subscription for the $19
one-time"]. Keep it that way.

## 1. One-line positioning
"[The truest single sentence a buyer would nod at — problem + honest differentiator, no overclaim.]"

## 2. Who buys this at [PRICE] (segments — go where they already are)
- [Segment 1] — [the specific communities/subreddits/groups they gather in]
- [Segment 2] — [where]
- [Segment 3] — [where]
(Reach segments, not scraped individuals — post where they gather; let them opt in.)

## 3. Landing blurb (site / social bio / Show-HN style)
> [2–4 sentences: what it is, the honest differentiator, what it is NOT, price, soft CTA
> ("try the free view, upgrade for X"). No fabricated stats, no fake urgency.]

## 4. Outreach templates (honest, no overclaim — you press send)
A) Cold email / DM:
> Subject: [plain, honest subject]
> Hi [name] — I built [PRODUCT], [one honest sentence]. The thing I care about: [differentiator].
> It's [what it is], not [what it isn't]. [link] — would love your sharp critique.
B) Community post (Reddit / Discord / Facebook Group / X):
> [Problem I had] → so I built [PRODUCT], [honest one-liner]. Free to look; [price] for the full
> thing. Tear it apart: [link]  (respect each community's self-promo rules)
C) Short "Show HN"-style intro:
> Show [venue]: [PRODUCT] — [honest one-liner]. [price]. [link]

## 5. First-buyer sequence (~20 minutes)
1. Post landing blurb (§3) to your own channels + bio.
2. Send template B to 2–3 relevant communities (respect each one's self-promo rules).
3. Send template A to 5–10 people you can reach honestly.
4. Watch for the first checkout on the live link. When it lands it's a real dollar — verify it
   SETTLED in Stripe before claiming EARNING (no fake green).

## 6. Guardrails (do not cross)
- No fabricated stats, no fake endorsements, no quotes attributed to real people who didn't say them.
- Never weaken [the product-specific honesty line from the header].
- Don't imply [the specific misuse this product must not claim].
- Nothing personal — product value only.
```

**Template structure at a glance:** header (gate check + live link + price + honesty rule) →
(1) one-line positioning → (2) who-buys + where-they-gather → (3) landing blurb → (4) three
outreach templates (cold DM / community post / Show-HN) → (5) ~20-min first-buyer sequence →
(6) guardrails.

---

## 5. Worked example — the template is already instantiated for Epic Fury

`docs/founder/epic_fury_first_buyer_kit.md` **is** this template filled in for the one product
currently past the gate. Use it as the reference when instantiating the next CLEARED product.
The next products to receive a filled kit will be whichever flips to rung 4 first — most likely
**Story Studio** (once the Stripe key/price mismatch is fixed and checkout returns a real session).

---

## 6. Etiquette summary (applies to every channel, every product)

- **Disclose you're the maker, always.** No "look what I found" framing for your own product.
- **One honest post per community**, following its self-promo rules. Respect the room.
- **Invite critique.** The goal is a real buyer and honest feedback, not vanity metrics.
- **Never fabricate** testimonials, reviews, user counts, endorsements, or urgency.
- **Never market a broken checkout** or a product below rung 4.
- **Nothing personal.** Product value to the buyer only.

---

## 7. The funnel — honest post → live checkout → first settled dollar

```
[Honest post/DM]  →  [Live checkout link (rung 4 verified)]  →  [Real Stripe session]
      →  [Charge succeeds]  →  [Balance transaction SETTLES]  →  claim "EARNING" (rung 5)
```

Rules on the funnel:
1. **Entry is gated by §1.** A post only goes out for a rung-4 product. No exceptions.
2. **The link is the real, live checkout** — never a placeholder, never a preview page dressed up
   as a buy button.
3. **A `succeeded` charge is NOT settled money.** Confirm a **balance transaction** in Stripe
   (Pending → Available) before anyone says "we earned." A completed checkout = SALE PENDING;
   only a settled balance transaction = EARNING.
4. **Measure honestly:** count real sessions and real settled dollars. Do not report impressions
   or clicks as revenue. Do not claim a gate done that still needs verification. NO FAKE GREEN.

---

## 8. One-paragraph operating summary

Every product stays marketing-silent until its checkout returns a real Stripe session (rung 4).
The instant it does, fill the §4 template, post honestly on the channel that fits its buyer
(LinkedIn for analyst/B2B products like Epic Fury; Facebook for consumer products like Story
Studio; light organic everywhere), drive to the live checkout, and only claim "earning" once a
balance transaction settles. Today that means: **run Epic Fury's kit now; hold everything else,
Story Studio included, until its checkout is verified live.**
