# cues/ — DROP LICENSE-CLEARED AUDIO HERE (none shipped)

This directory is where real, **license-cleared, instrumental-only** cue audio lives.
**There is intentionally NO audio in this repo.** The store engine, license gate,
packaging, and delivery are all REAL and tested — the ONLY missing piece is the
audio itself, which the founder must supply. Shipping placeholder tones would be
FAKE GREEN.

## What the founder must do

For each pack in `../catalog/catalog.json`, create a subfolder and drop the tracks
that the manifest references, then flip that pack's `"available": true`.

```
cues/
  midnight-drive/
    md-01.wav   md-02.wav   md-03.wav   md-04.wav
  sunrise-standup/
    ss-01.wav   ss-02.wav   ss-03.wav
```

The file names must match the `"file"` fields in `catalog/catalog.json`.

## HARD GUARDRAILS (enforced by engine/gate.js — non-negotiable)

- **Instrumental only. No vocals, no lyrics.** (`vocals` must be `false`.)
- **No artist- or voice-likeness of any real person.** No "in the style of <named
  artist>" material. (`artist_likeness` must be `false`.)
- **Every track must be license-cleared** — you own it or hold a redistribution-
  and-sublicense-clean license for it. HMF's delivered `LICENSE.txt` sublicenses
  it to buyers; you cannot grant rights you don't hold.
- **License gate is mandatory.** Delivery only happens after (1) an active
  entitlement AND (2) the per-file policy gate passes. Missing/empty files, or any
  track flagged vocal/likeness, block the whole pack — fail-closed.

Until you drop cleared audio and flip `"available": true`, `/api/download` returns
`503 no_audio_yet` for entitled users and `403 not_entitled` for everyone else —
by design.
