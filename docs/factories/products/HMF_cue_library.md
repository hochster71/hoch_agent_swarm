# HMF Product — "HOCH Cue Library" (Cleared Instrumental Cues)

**Factory:** HMF · Hoch Music Factory · *Soundtrack · Media Audio (feeds content)*
**Registry:** `coordination/products/product_registry.json` → `HMF_CUE_LIBRARY`
**Rung today:** 3 · PRODUCTIZED (defined only) — no validated cue pack yet, no checkout, $0 earned.
**Status:** first-mission spec STAGED. Do **not** dispatch during the active soak. Dispatch after seal.

## Product

Themed packs of original **instrumental** music cues — loops, stings, beds, transitions — license-cleared for use in video, podcasts, and indie games. Sold as monthly access to a growing cue library.

**Price:** $9/mo ($90/yr). **Buyer:** video creators, podcasters, indie game devs needing cheap, license-clean background music.

**Hard guardrails (policy, non-negotiable before anything ships):**
- **Instrumental-first:** no vocals, no lyrics.
- **No artist- or voice-likeness** of any real person.
- **License-gate:** every cue ships with an explicit usage license; nothing leaves the factory without passing the license gate. (HMF's stated design is already "instrumental-first, license gate.")

## First mission (dispatch after soak seals)

> **Goal:** produce HMF's first validated artifact — one small cue pack (e.g. 3 royalty-clean instrumental beds) with attached licenses — so the factory moves DECLARED → PRODUCES.

- **Output artifact:** `cue_pack_<theme>_<UTC>/` containing 3 instrumental audio files + `LICENSE.txt` + a manifest, under `docs/scratch/artifacts/`.
- **Acceptance:** files are audio and non-empty; manifest lists each cue + duration; license-gate check passes for every file; automated check confirms no vocal stem / no named-artist metadata.
- **Definition of done for this rung:** one validated, license-clean pack exists → census shows HMF at PRODUCES (2), not DECLARED (0).

## Path to first dollar (later, founder-gated at the checkout step)

PRODUCES → PRODUCTIZED (done: name+price) → **SELLABLE** (needs a checkout: Stripe product + a place to browse/download packs — founder-gated) → EARNING. No checkout built yet; that step stops at the founder door.
