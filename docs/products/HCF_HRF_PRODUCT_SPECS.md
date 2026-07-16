# HCF & HRF Product Specs — Moonshot Blueprints
*2026-07-15 · grounded in what each factory actually produces · rail: Stripe · every money/publish step is founder-gated*

Guiding principle (Michael's): **solve a real problem for people, and turn a negative into a positive.**
Both products below start from a genuine harm and answer it with something protective and accessible.

---

## HCF — **CyberQRG-AI** · "Scan before you trust."

**The negative (real, growing):** QR-code scams — *"quishing"* — are surging. Fake QR stickers on
parking meters, restaurant tables, packages, delivery notices, and emails send people to phishing
pages or payment-stealing sites. The hardest hit are exactly the people least equipped to spot it:
the elderly and the non-technical.

**The positive:** a dead-simple scanner that answers one question — *"Is this QR safe?"* — **before**
you act on it. Offline-first, so it works anywhere and keeps the scan private.

**What already exists (rung ~2–3):** `products/cyberqrg-ai/` — a real TypeScript package, **offline-first,
zero external internet dependency**, with schema / security-policy / UI-smoke test suites and a
`SECURITY.md`. This isn't a blank page; it's a working prototype.

**Product**
- **Name:** CyberQRG-AI
- **Buyer:** everyday phone users worried about scams; adult children protecting elderly parents;
  small shops wanting to reassure customers.
- **What they get:** point the phone at a QR → an instant, plain verdict *before* it opens —
  reveal the real destination domain, flag look-alike/homograph domains, catch redirect chains and
  known-scam URL patterns, all via offline heuristics. Green = go, amber = look closer, red = don't.
- **Price (Stripe):** deliberately cheap so it protects the most people — **free** basic scan;
  **$0.99/mo "Family Protect"** (unlimited scans + an optional "check-in" alert a caretaker can see).
  Accessibility *is* the strategy here.

**Path to shipped**
1. Wrap the existing package as an app (iOS — same pipeline that shipped Epic Fury — and/or a web PWA).
2. Ship the scan → verdict UX with the offline heuristic set already scaffolded.
3. Stripe: one product, $0.99/mo recurring. **Founder gate:** App Store / Stripe keys + deploy.

**Why it matters:** it takes a scam epidemic and hands ordinary people a five-second shield. That's the
North Star's "monetized products that help humanity" in one clean example.

---

## HRF — **Clarity Briefs** · "The truth, in plain English, with receipts."

**The negative:** the research that affects real decisions — health, money, policy, tech — is buried in
jargon and paywalls, and misinformation rushes into the gap. People are asked to trust vibes over sources.

**The positive:** turn complex, credible material into **short, cited, jargon-free briefs** anyone can
read and verify — clarity with receipts, not hot takes.

**What already exists (rung 2):** HRF has produced 500+ synthesis/comparison artifacts — the exact
muscle a briefing product needs: read sources, compare, cite, explain. It produces; it just has no
named product.

**Product**
- **Name:** Clarity Briefs
- **Buyer:** curious non-experts, teachers, caregivers, small-business owners, journalists — anyone who
  wants a sourced answer they can trust and pass along.
- **What they get:** a weekly brief on a chosen topic (or on-demand one-offs) — balanced, plain-English,
  every claim linked to a real source, with an explicit "what's still uncertain" section (no false
  confidence — same doctrine as HELM).
- **Price (Stripe):** **$5/mo** subscription, or **$2** per one-off brief.

**Path to shipped**
1. Define one launch vertical (e.g., "everyday health claims, decoded") so the buyer is concrete.
2. Reuse HRF's synthesis pipeline; enforce a citation-per-claim rule + an uncertainty section.
3. Simple web reader + Stripe checkout. **Founder gate:** Stripe keys + deploy.

**Why it matters:** it fights misinformation with sourced clarity — a positive built directly on top of
a negative, and honest by construction (it labels what it doesn't know).

---

## For the moonshot swarm (tomorrow)
- **MOON-HCF-01** → build toward **CyberQRG-AI** (productize the existing scanner; $0.99/mo).
- **MOON-HRF-01** → build toward **Clarity Briefs** (define the launch vertical; $5/mo or $2/brief).
- Both stop at the founder gate for keys/deploy/publish. Rungs are earned and observed by
  `factory_census`, never asserted — no product claims EARNING without a settled dollar.
