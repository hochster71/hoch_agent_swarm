# stings/ — founder-supplied audio goes here

This directory is intentionally EMPTY of audio. No real audio ships with this repo.

The catalog (`catalog/catalog.json`) lists sting files under `stings/<pack_id>/`,
but every pack is marked `"available": false` and those files DO NOT exist yet.

To ship a pack for real, the founder must:

1. Produce (or license) **instrumental-only** stings/transitions — **no vocals,
   no lyrics, no artist- or voice-likeness** (the policy gate in `engine/gate.js`
   enforces this and fails closed).
2. Drop the cleared `.wav` files into `stings/<pack_id>/` matching the catalog's
   `file` paths (e.g. `stings/cold-open/co-01.wav`).
3. Flip that pack's `"available": true` in `catalog/catalog.json`.

Until then, delivery runs in PLACEHOLDER mode: the license gate and packaging are
REAL and exercised, but the ZIP contains a `README_NO_AUDIO.txt` instead of fake
tones. Shipping placeholder audio as a product would be FAKE GREEN.
