"""Per-factory voice briefs — registered factories only (HASF/HMF/HRF).

Doctrine: observe BRAIN state paths; UNKNOWN when missing/stale; never invent convergence.
Declared-but-unregistered factories (HSF/HCF/HFF/…) return PLANNED, not LIVE.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.factory.registry import Factory, list_factories
from backend.voice.policy import load_voice_policy
from backend.voice.sanitizer import sanitize_for_speech

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "UNKNOWN"

# Declared factories with dedicated observers (not full BRAIN registry)
_EXTENDED_META: Dict[str, Dict[str, str]] = {
    "HSF": {"title": "Hoch Storybook Factory", "kind": "DECLARED_OBSERVABLE"},
    "HCF": {"title": "Hoch Cybersecurity Factory", "kind": "DECLARED_OBSERVABLE"},
    "HFF": {"title": "Hoch Finance Factory", "kind": "DECLARED_OBSERVABLE"},
    "HHF": {"title": "Hoch Home Factory", "kind": "DECLARED_OBSERVABLE"},
    "HPF": {"title": "Hoch Prompt Factory", "kind": "DECLARED_OBSERVABLE"},
}

_CODE_ALIASES = {
    "HASF": "software",
    "SOFTWARE": "software",
    "HMF": "music",
    "MUSIC": "music",
    "HRF": "research",
    "RESEARCH": "research",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _freshness_label(mtime: Optional[float]) -> str:
    if mtime is None:
        return "UNKNOWN"
    age = time.time() - mtime
    budget = float(load_voice_policy().get("freshness_budget_seconds") or 300)
    if age > budget:
        return "STALE"
    return "LIVE"


def _read_json(path: Path) -> tuple:
    """Returns (data_or_None, mtime_or_None, error_or_None)."""
    try:
        if not path.exists():
            return None, None, "missing"
        mtime = path.stat().st_mtime
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, mtime, None
    except Exception as e:
        return None, None, str(e)


def resolve_factory(code_or_domain: str) -> Optional[Factory]:
    key = (code_or_domain or "").strip()
    if not key:
        return None
    upper = key.upper()
    domain = _CODE_ALIASES.get(upper) or key.lower()
    for f in list_factories():
        if f.domain == domain or f.code.upper() == upper:
            return f
    return None


def list_factory_voice_roster() -> List[Dict[str, Any]]:
    """All factories voice can talk about: BRAIN-registered + declared-observable."""
    out: List[Dict[str, Any]] = []
    for f in list_factories():
        out.append(
            {
                "code": f.code,
                "domain": f.domain,
                "title": f.title,
                "registry": "REGISTERED",
                "voice_status": "AVAILABLE",
                "path": f"/api/v1/helm/voice/factory/{f.code}",
            }
        )
    for code, meta in _EXTENDED_META.items():
        out.append(
            {
                "code": code,
                "domain": UNKNOWN,
                "title": meta["title"],
                "registry": meta["kind"],
                "voice_status": "OBSERVABLE_PARTIAL",
                "path": f"/api/v1/helm/voice/factory/{code}",
            }
        )
    return out


def observe_factory(code_or_domain: str) -> Dict[str, Any]:
    """Build a fail-closed factory observation + speech brief."""
    code_raw = (code_or_domain or "").strip().upper()
    fac = resolve_factory(code_or_domain)

    if fac is None:
        # Extended declared factories (HSF/HCF/HFF/HPF/HHF)
        if code_raw in _EXTENDED_META:
            from backend.voice.extended_factories import EXTENDED_OBSERVERS

            observer = EXTENDED_OBSERVERS.get(code_raw)
            if observer:
                return observer()
        speech = (
            f"Factory '{code_or_domain}' is not registered and not in the observable roster. "
            f"Status UNKNOWN."
        )
        return {
            "truth_class": "HELM_VOICE_FACTORY",
            "status": "UNKNOWN",
            "code": code_raw or UNKNOWN,
            "observed_at": _now(),
            "speech_text": sanitize_for_speech(speech),
            "labels": {"factory": "UNKNOWN"},
            "data": {"reason": "not in registry"},
        }

    conv, conv_m, conv_err = _read_json(fac.convergence_status)
    champ, champ_m, champ_err = _read_json(fac.champion_registry)
    genes, genes_m, genes_err = _read_json(fac.gene_pool)

    labels: Dict[str, str] = {
        "factory": "LIVE",
        "convergence": _freshness_label(conv_m) if not conv_err else "UNKNOWN",
        "champions": _freshness_label(champ_m) if not champ_err else "UNKNOWN",
        "genes": _freshness_label(genes_m) if not genes_err else "UNKNOWN",
    }

    # Convergence detail
    state = UNKNOWN
    mean_score = None
    generation = None
    if isinstance(conv, dict):
        state = str(conv.get("state") or conv.get("status") or UNKNOWN)
        mean_score = conv.get("mean_score")
        generation = conv.get("generation")

    # Champions
    champ_count = None
    if isinstance(champ, dict):
        ch = champ.get("champions")
        if isinstance(ch, dict):
            champ_count = len(ch)
        elif isinstance(ch, list):
            champ_count = len(ch)

    # Genes
    gene_count = None
    if isinstance(genes, dict):
        g = genes.get("genes")
        if isinstance(g, dict):
            gene_count = len(g)
        elif isinstance(g, list):
            gene_count = len(g)

    # Overall status: if all core sources missing → UNKNOWN; any STALE → STALE if otherwise ok
    if conv_err and champ_err and genes_err:
        overall = "UNKNOWN"
        labels["factory"] = "UNKNOWN"
    elif "STALE" in labels.values():
        overall = "STALE"
        labels["factory"] = "STALE"
    elif "UNKNOWN" in (labels["convergence"], labels["champions"], labels["genes"]):
        overall = "PARTIAL"
    else:
        overall = "LIVE"

    parts = [
        f"{fac.code} — {fac.title}.",
        f"Domain {fac.domain}.",
        f"Convergence state: {state}"
        + (f", mean score {mean_score}" if mean_score is not None else "")
        + (f", generation {generation}" if generation is not None else "")
        + f" [{labels['convergence']}].",
    ]
    if champ_count is not None:
        parts.append(f"Champions observed: {champ_count} [{labels['champions']}].")
    else:
        parts.append(f"Champions: UNKNOWN [{labels['champions']}].")
    if gene_count is not None:
        parts.append(f"Genes observed: {gene_count} [{labels['genes']}].")
    else:
        parts.append(f"Genes: UNKNOWN [{labels['genes']}].")
    parts.append(f"Publish tier {fac.publish_tier}. Gates: {', '.join(fac.gates)}.")
    parts.append(
        "T3 publish and deploy require founder approval. Voice will not clear them."
    )
    if overall in ("STALE", "PARTIAL", "UNKNOWN"):
        parts.append(f"Overall factory voice status: {overall}.")

    return {
        "truth_class": "HELM_VOICE_FACTORY",
        "status": overall,
        "code": fac.code,
        "domain": fac.domain,
        "title": fac.title,
        "registry": "REGISTERED",
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": {
            "convergence_state": state if state != UNKNOWN or conv else None,
            "mean_score": mean_score,
            "generation": generation,
            "champion_count": champ_count,
            "gene_count": gene_count,
            "gates": list(fac.gates),
            "publish_tier": fac.publish_tier,
            "paths": {
                "convergence": str(fac.convergence_status.relative_to(ROOT)),
                "champions": str(fac.champion_registry.relative_to(ROOT)),
                "genes": str(fac.gene_pool.relative_to(ROOT)),
            },
            "source_errors": {
                k: v
                for k, v in {
                    "convergence": conv_err,
                    "champions": champ_err,
                    "genes": genes_err,
                }.items()
                if v
            },
        },
        "doorstep": list(fac.gates),
        "freshness_seconds": {
            "convergence": (time.time() - conv_m) if conv_m else None,
            "champions": (time.time() - champ_m) if champ_m else None,
            "genes": (time.time() - genes_m) if genes_m else None,
        },
    }


def observe_all_registered_factories() -> Dict[str, Any]:
    briefs = [observe_factory(f.code) for f in list_factories()]
    # Include extended declared factories in roster speech (compact)
    for code in _EXTENDED_META:
        try:
            briefs.append(observe_factory(code))
        except Exception:
            continue
    lines = [b["speech_text"] for b in briefs]
    statuses = [b["status"] for b in briefs]
    overall = "LIVE"
    if any(s in ("UNKNOWN", "PARTIAL", "PLANNED") for s in statuses):
        overall = "PARTIAL"
    if all(s == "UNKNOWN" for s in statuses):
        overall = "UNKNOWN"
    if any(s == "STALE" for s in statuses) and overall == "LIVE":
        overall = "STALE"
    return {
        "truth_class": "HELM_VOICE_FACTORY_ROSTER",
        "status": overall,
        "observed_at": _now(),
        "factories": briefs,
        "speech_text": sanitize_for_speech(" ".join(lines)[:2000]),
        "roster": list_factory_voice_roster(),
    }
