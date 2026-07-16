# HMF Cue Library — Engine Build Spec

**Product:** `HMF_CUE_LIBRARY` — "HOCH Cue Library: cleared instrumental cues for creators" ($9/mo, $90/yr)
**Factory:** HMF · Hoch Music Factory
**Today's real state:** checkout scaffold (`products/hmf-cue-library/` — landing + `api/create-checkout-session.js`, fail-safe 501) with an **empty** `public/cues/PLACEHOLDER.md`, plus a mission spec (`docs/factories/products/HMF_cue_library.md`). **There is no cue-production engine and there are zero real cues.** This spec defines the engine.
**Rung:** 3 (defined) → target 4 (sellable) once real, license-clean cues exist behind the buy-gate.

---

## What to build

An **instrumental-cue production + license-gate pipeline** that yields themed packs of original **instrumental** cues (loops, stings, beds, transitions), each shipped with an explicit usage license, browsable/downloadable **only after purchase**. Two halves: (a) produce & QC the cues, (b) gate delivery on both purchase and the license/policy check.

**Pipeline (5 stages):**
1. **Spec** — define a cue-pack recipe (theme, genre, structure, tempo/key, mood arc) as a scored spec.
2. **Score/gate the recipe** — run the recipe through the existing mechanical scorer before any audio is made (catches under-specified or originality-risky recipes early).
3. **Produce audio** — render instrumental cues (v1 can start from licensed/royalty-clean instrumental source material or an instrumental-only generation path; **no vocals, no voice, no artist cloning**). Each cue: instrumental stem only, with duration + metadata.
4. **License-gate & QC** — for every file: confirm it is audio + non-empty; confirm **no vocal stem** and **no named-artist metadata**; attach `LICENSE.txt`. Nothing leaves the factory without passing this gate.
5. **Package & deliver** — assemble `cue_pack_<theme>_<UTC>/` (audio files + `LICENSE.txt` + manifest); publish behind the purchase gate so only paying buyers can download.

## Inputs / Outputs

- **Input:** a cue-pack recipe `{ theme, genre, structure, tempo, key, count }`.
- **Output:** `cue_pack_<theme>_<UTC>/` = N instrumental audio files + `manifest.json` (per-cue: title, duration, bpm, key, license id) + `LICENSE.txt`. Delivered via signed/gated download post-purchase.

## Reuse from this repo

- **Checkout shell:** `products/hmf-cue-library/` (already built, incl. `public/cues/` delivery dir) + the `products/cyberqrg-ai/deploy` Vercel + serverless checkout pattern.
- **Recipe scorer (real, already written):** `backend/brain_convergence/music_scorer.py` — a `MECHANICAL_PROXY` scorer that grades a music recipe on genre, structure, hook, **originality (a governance gate that weights against cloning a named artist)**, instrumentation, mix/master spec, etc. Use it as the stage-2 recipe gate. Config lives in `config/music_score_rubric.yaml`; genes seed via `scripts/seed_music_genes.py` and `data/prompt_brain/music`.
- **Audio integration reference:** `backend/voice/elevenlabs_tts.py` shows the ElevenLabs API-call + credential-from-env pattern to mirror for an audio provider (note: that path is TTS; music generation needs a *music* model/source — the calling pattern is the reusable part, not the voice endpoint).
- **Fail-closed gate pattern:** reuse the repo's gate idiom (e.g. `scripts/anti_fake_gate.sh`) for the license/no-vocals check.

## Guardrail (HARD, non-negotiable)

**Instrumental-first: no vocals, no lyrics. No artist- or voice-likeness of any real person. License-gate on every file.** The scorer already treats originality as a governance gate; the delivery pipeline must additionally, per file, verify no vocal stem and no named-artist metadata, and refuse to package any cue lacking a clean license. Music generation must not clone a named artist's style/voice. Delivery is gated on purchase AND on passing this policy check — fail-closed.

## Definition of done (shell → sellable)

- At least **one real, validated, license-clean cue pack** exists behind the buy-gate (replaces `PLACEHOLDER.md`): ≥3 instrumental files that are audio + non-empty, with a manifest and `LICENSE.txt`.
- The license/no-vocals QC check runs on every file and **fails closed** on a seeded vocal-containing test file (proves the gate is real).
- The recipe passes `music_scorer` above threshold before production; originality gate demonstrably rejects a "in the style of <named artist>" recipe.
- Post-purchase, a buyer can download the pack; a non-buyer cannot.

## Honest effort estimate

**Effort concentrates in the audio-production half, and there's a real dependency decision.** The scorer, rubric, checkout, and delivery dir already exist — the recipe-gate and packaging are quick. The open question is *how the actual audio gets made*: sourcing royalty-clean instrumental material vs. an instrumental-only generation model. v1 is fastest if it curates/licenses existing royalty-clean instrumental source and applies the license-gate + packaging (days). A from-scratch generation path is a larger, separate build. Either way the no-vocals / no-likeness gate is mandatory before a single cue ships.
