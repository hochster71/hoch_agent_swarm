#!/usr/bin/env python3
"""Seed the HMF music gene pool with honest, well-specified starter recipes (labeled SEED).

Each gene is a *track recipe* (genre, structure, hook, originality, instrumentation, tempo/key,
mix/master, arc, metadata, QC) — a real production spec, NOT a claim that any finished audio is
good. task_class = genre, so the same gap-analysis that finds thin software classes finds thin
genres. Deterministic: content-hash per recipe, class_sizes computed, written in the exact
brain-convergence gene-pool schema so the domain-agnostic engine consumes it unchanged.
"""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prompt_brain" / "music" / "gene_pool.json"

# (genre, title, recipe). Deliberately varied completeness + some single-gene genres so thin-pool
# detection fires just like it does for software.
SEEDS = [
    ("Lo-Fi Hip-Hop", "Rainy Study Loop",
     "Genre: lo-fi hip-hop, dusty boom-bap feel (style of the genre, not any named artist). "
     "Structure: intro (4 bars) → main loop A (verse) → variation B (chorus) → bridge with filter "
     "sweep → outro tape-stop. Hook: a 4-note Rhodes motif is the memorable center. Originality: "
     "original composition, royalty-free/cleared samples only, no sampling of any named recording. "
     "Instrumentation: Rhodes piano, upright bass, vinyl-crackle drums, soft 808, brush snare, pads. "
     "Tempo/key: 82 BPM, key of F minor, 4/4 swing groove. Mix/master: warm, target -14 LUFS, gentle "
     "sidechain, mono-safe bass, stereo pads. Arc: low energy build, small lift into B, resolve. "
     "Metadata: title, mood tags (calm, nostalgic), duration ~2:30. QC: A/B reference-check mix "
     "before render is accepted."),
    ("Lo-Fi Hip-Hop", "Late Night Walk",
     "Genre: lo-fi hip-hop, jazzy late-night feel. Structure: intro → loop A → loop B (chorus lift) "
     "→ outro. Hook: muted trumpet topline motif. Originality: original, cleared sources only. "
     "Instrumentation: muted trumpet, Rhodes, sub bass, lo-fi drums, rain foley. Tempo/key: 75 BPM, "
     "key of D minor, 4/4. Mix/master: -14 LUFS, warm EQ, tape saturation. Arc: steady, gentle swell. "
     "Metadata: title, mood (mellow), ~2:10. QC: mix check before render."),
    ("Deep House", "Sunset Terrace",
     "Genre: deep house, organic/melodic (genre style only). Structure: intro → build → drop A "
     "(chorus) → breakdown (bridge) → drop B → outro. Hook: plucked synth topline riff. Originality: "
     "original composition, no clone of any named artist, cleared one-shots. Instrumentation: deep "
     "sub bass, analog pads, plucked synth, shaker, congas, filtered vocal chops. Tempo/key: 122 BPM, "
     "A minor, 4/4 four-on-the-floor. Mix/master: club-ready -8 LUFS, wide stereo pads, mono bass, "
     "sidechain compression. Arc: build tension → release on drop. Metadata: title, tags (warm, "
     "groovy), ~3:30. QC: reference A/B against a deep-house loudness target."),
    ("Melodic Techno", "Aurora Drive",
     "Genre: melodic techno, hypnotic. Structure: intro → rolling groove → breakdown build → drop → "
     "outro. Hook: arpeggiated lead motif. Originality: original, copyright-safe, no named-artist "
     "imitation. Instrumentation: driving bass, analog arps, atmospheric pads, rimshot, noise riser. "
     "Tempo/key: 124 BPM, F# minor, 4/4. Mix/master: -8 LUFS, controlled low end, wide reverb tails. "
     "Arc: slow hypnotic build, energy peak at drop. Metadata: title, mood (driving, cosmic), ~4:00. "
     "QC: mix check before render."),
    ("Ambient", "Glacier Fields",
     "Genre: ambient, cinematic drone (style of the genre). Structure: evolving single movement with "
     "intro swell → dense mid → sparse outro (no beat). Hook: a recurring bell motif surfaces. "
     "Originality: original, cleared field recordings only. Instrumentation: granular pads, soft "
     "bells, sub drone, processed field recordings. Tempo/key: rubato, key of C major, no strict "
     "meter. Mix/master: spacious, -16 LUFS, wide stereo, gentle high shelf. Arc: slow swell and "
     "decay. Metadata: title, mood (serene), ~5:00. QC: reference listen for masking before render."),
    ("Ambient", "Signal Rain",
     "Genre: ambient textural. Structure: drone bed → texture layer → resolve. Hook: filtered pad "
     "motif. Originality: original, no sampling of named works. Instrumentation: pads, tape noise, "
     "sub. Tempo/key: free, D major. Mix/master: -16 LUFS, wide. Arc: gradual. Metadata: title, mood "
     "(hazy), ~4:20. QC: A/B check."),
    ("Drum & Bass", "Neon Current",
     "Genre: liquid drum & bass. Structure: intro → drop A (chorus) → breakdown → drop B → outro. "
     "Hook: vocal-chop topline. Originality: original, cleared sources, no named-artist clone. "
     "Instrumentation: reese bass, chopped breaks, lush pads, piano stabs. Tempo/key: 174 BPM, G "
     "minor, 4/4. Mix/master: -8 LUFS, tight low end, wide reverb. Arc: energetic, rolling. Metadata: "
     "title, mood (uplifting), ~3:40. QC: reference A/B before render."),
    ("Synthwave", "Midnight Highway",
     "Genre: synthwave / retrowave. Structure: intro → verse → chorus → bridge → chorus → outro. "
     "Hook: analog lead melody. Originality: original, no clone of named artists, cleared samples. "
     "Instrumentation: gated drums, analog bass, saw leads, lush pads, arps. Tempo/key: 100 BPM, E "
     "minor, 4/4. Mix/master: -10 LUFS, wide chorus, retro reverb. Arc: nostalgic build to big "
     "chorus. Metadata: title, mood (retro, driving), ~3:20. QC: mix check."),
    ("Cinematic Score", "Rising Tide",
     "Genre: cinematic orchestral hybrid. Structure: intro → theme statement → development → climax → "
     "resolution. Hook: a string/brass main theme motif. Originality: original composition, no "
     "borrowed themes, cleared libraries. Instrumentation: strings, brass, hybrid percussion, piano, "
     "sub boom. Tempo/key: 90 BPM, D minor, 4/4. Mix/master: wide orchestral image, -16 LUFS, dynamic "
     "range preserved. Arc: slow build to a climactic peak, then resolve. Metadata: title, mood "
     "(epic, hopeful), ~2:45. QC: reference A/B for dynamics before render."),
    ("Afrobeats", "Lagos Morning",
     "Genre: afrobeats/afropop. Structure: intro → verse → chorus (hook) → verse → chorus → outro. "
     "Hook: call-and-response topline. Originality: original, cleared percussion one-shots, no "
     "named-artist imitation. Instrumentation: log drum, shakers, plucked guitar, marimba, sub bass. "
     "Tempo/key: 105 BPM, A major, 4/4. Mix/master: punchy -8 LUFS, mono bass, bright top. Arc: "
     "groovy, steady lift into chorus. Metadata: title, mood (sunny, danceable), ~3:10. QC: A/B "
     "reference before render."),
]


def _hash(t: str) -> str:
    return hashlib.sha256(t.strip().encode()).hexdigest()


def build():
    genes = {}
    sizes = {}
    for i, (genre, title, recipe) in enumerate(SEEDS):
        h = _hash(recipe)
        gid = f"seed-{genre[:4].lower().replace(' ', '')}-{h[:10]}"
        genes[gid] = {
            "gene_id": gid, "task_class": genre, "title": title,
            "prompt": recipe, "content_hash": h, "state": "SEED",
            "source": "HUMAN_SEED", "domain": "music",
        }
        sizes[genre] = sizes.get(genre, 0) + 1
    pool = {
        "schema": "brain-convergence-gene-pool-m0", "domain": "music",
        "count": len(genes),
        "class_sizes": dict(sorted(sizes.items(), key=lambda x: -x[1])),
        "task_classes": len(sizes), "genes": genes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pool, indent=2), encoding="utf-8")
    print(f"seeded {len(genes)} music genes across {len(sizes)} genres -> {OUT}")


if __name__ == "__main__":
    build()
