"""HMF music scorer — MECHANICAL PROXY for a track recipe's production-readiness.

Drop-in twin of scorer.py (same `score_prompt(text, rubric_path) -> {overall, dimensions, method,
rung}` signature) so the domain-agnostic BRAIN engine can score the music gene pool with no change.

HONESTY BOUNDARY: this scores whether a music *recipe/spec* contains the disciplines a producer
would want (genre, structure, hook, originality, mix/master, ...). It does NOT and CANNOT judge how
the finished audio sounds — that verdict requires an audio judge or a human A/B listen. Output is
labeled MECHANICAL_PROXY and rung=1. A high score means 'well-specified', never 'sounds great'.
Originality is weighted high because it is a HAS governance gate (never clone a named artist).
"""
from pathlib import Path
from typing import Dict, Any, Optional

_DEFAULT_WEIGHTS = {
    "genre_fidelity": 0.15, "song_structure": 0.12, "hook_strength": 0.12,
    "originality_declared": 0.12, "instrumentation": 0.10, "rhythm_tempo_key": 0.10,
    "mix_master_spec": 0.10, "emotional_arc": 0.07, "metadata_complete": 0.07,
    "production_qc": 0.05,
}

# Signal keywords per dimension (lowercased substring match). Threshold = hits for full marks.
_SIGNALS = {
    "genre_fidelity": (["genre", "subgenre", "style of ", "in the style", "feel", "vibe", "reference track", "era"], 2),
    "song_structure": (["intro", "verse", "chorus", "bridge", "drop", "outro", "section", "arrangement", "pre-chorus"], 2),
    "hook_strength": (["hook", "topline", "motif", "riff", "melody", "earworm", "lead line", "refrain"], 1),
    "originality_declared": (["original", "no clone", "not in the style of a named", "royalty-free", "cleared", "no sampling of", "own composition", "copyright-safe"], 1),
    "instrumentation": (["synth", "drums", "bass", "guitar", "piano", "pads", "808", "strings", "vocal", "instrument"], 2),
    "rhythm_tempo_key": (["bpm", "tempo", "key of", " key ", "time signature", "groove", "swing", "4/4"], 1),
    "mix_master_spec": (["mix", "master", "lufs", "loudness", "stereo", "eq", "compression", "reference level", "headroom"], 2),
    "emotional_arc": (["energy", "dynamics", "build", "tension", "release", "arc", "mood progression", "drop energy"], 1),
    "metadata_complete": (["title", "tags", "mood", "duration", "length", "isrc", "bpm/key metadata"], 2),
    "production_qc": (["reference check", "qa", "listen test", "a/b", "mix check", "review before render", "verify mix"], 1),
}


def _load_weights(rubric_path: Optional[str]) -> Dict[str, float]:
    if not rubric_path or not Path(rubric_path).exists():
        return dict(_DEFAULT_WEIGHTS)
    try:
        import yaml
        d = yaml.safe_load(Path(rubric_path).read_text())["dimensions"]
        return {k: float(v["weight"]) for k, v in d.items()}
    except Exception:
        return dict(_DEFAULT_WEIGHTS)


def score_prompt(text: str, rubric_path: Optional[str] = None) -> Dict[str, Any]:
    """MECHANICAL_PROXY score of a music recipe's production-readiness. Same shape as scorer.py."""
    t = (text or "").lower()
    weights = _load_weights(rubric_path)
    dims: Dict[str, float] = {}
    for dim, (kws, thresh) in _SIGNALS.items():
        hits = sum(1 for k in kws if k in t)
        dims[dim] = min(1.0, hits / thresh) if thresh else 0.0
    overall = round(100.0 * sum(dims[d] * weights.get(d, 0.0) for d in dims), 2)
    return {"overall": overall, "dimensions": dims,
            "method": "MECHANICAL_PROXY", "rung": 1,
            "note": "recipe-readiness only; audio quality needs an audio judge / human A-B listen"}


def compare(candidate_text: str, incumbent_text: str, rubric_path: Optional[str] = None) -> Dict[str, Any]:
    c = score_prompt(candidate_text, rubric_path)["overall"]
    i = score_prompt(incumbent_text, rubric_path)["overall"]
    return {"candidate": c, "incumbent": i, "delta": round(c - i, 2), "candidate_wins": c > i}


# Wire in live-outcomes blended scoring (2026-07-07)
from backend.brain_convergence.scorer import blended_score

