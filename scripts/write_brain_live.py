#!/usr/bin/env python3
"""Assemble the live BRAIN state into frontend/data/brain_live.json for the moonshot console.

Reads the real convergence + improvement + champion state and the live-model status, writes a
single small JSON the browser can fetch (served statically from frontend/). Called by
brain_cadence.sh each tick so the moonshot UI reflects live runtime. No fabrication — every field
comes from actual state files; missing files degrade to empty, never fake values.
"""
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "prompt_brain"
OUT = ROOT / "frontend" / "data" / "brain_live.json"


def _load(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def _factories_summary():
    """Per-factory live summary across ALL registered Factories (HASF/HMF/HRF/...).
    Each field comes from that domain's real state files; a domain that hasn't run yet shows its
    seeded gene count with state SEEDED — honest, never fabricated."""
    out = []
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from backend.factory.registry import list_factories
        for f in list_factories():
            gp = _load(f.gene_pool, {})
            genes = gp.get("count") or (len(gp.get("genes", {})) if isinstance(gp.get("genes"), dict) else 0)
            reg = _load(f.champion_registry, {})
            champs = len(reg.get("champions", {}))
            conv = _load(f.convergence_status, {})
            state = conv.get("state") or ("SEEDED" if genes else "EMPTY")
            out.append({
                "code": f.code, "domain": f.domain, "title": f.title,
                "genes": genes, "champions": champs,
                "mean_score": conv.get("mean_score"), "state": state,
                "gates": len(f.gates),
            })
    except Exception:
        pass
    return out


def build_live_state():
    """Assemble the live BRAIN state dict from real state files + live model detection.
    Reusable by both the static writer (main) and the /api/brain/live endpoint."""
    conv = _load(DATA / "convergence_status.json", {})
    reg = _load(DATA / "champion_registry.json", {})
    champs = reg.get("champions", {})

    improvements = []
    ip = DATA / "improved_champions.jsonl"
    if ip.exists():
        for line in ip.read_text().splitlines()[-10:]:
            try:
                d = json.loads(line)
                improvements.append({"task_class": d.get("task_class"), "beats_mech": d.get("beats_mech"),
                                     "score": d.get("score"), "at": d.get("at")})
            except Exception:
                pass

    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from backend.brain_convergence.local_model_bridge import status as brain_status
        live = brain_status()
    except Exception:
        live = {"live_brain_available": False}

    genes = _load(DATA / "gene_pool_m0.json", {}).get("count", 0)
    hist = conv.get("history", [])[-24:]

    # Meta lever + gap summary — so the console shows what the brain is doing and why.
    meta = _load(DATA / "research_meta_decision.json", {})
    gaps = _load(DATA / "gap_analysis.json", {})
    gap_summary = {
        "by_constraint": gaps.get("by_constraint", {}),
        "thin": len(gaps.get("thin_classes", [])),
        "low_ceiling": len(gaps.get("low_ceiling_classes", [])),
        "drift": len(gaps.get("taxonomy_drift", [])),
        "expansion_needed_genes": gaps.get("expansion_needed_genes"),
        "top5_share": (gaps.get("totals") or {}).get("top5_share"),
    } if gaps else {}

    out = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "live_brain": live,
        "generation": reg.get("generation", conv.get("generation", 0)),
        "genes": genes,
        "champions": len(champs),
        "mean_score": conv.get("mean_score", 0.0),
        "last_gain": conv.get("last_gain"),
        "state": conv.get("state", "UNKNOWN"),
        "meta_lever": meta.get("chosen_lever"),
        "meta_reason": meta.get("reason"),
        "global_converged": meta.get("global_converged", False),
        "gaps": gap_summary,
        "factories": _factories_summary(),
        "orchestrator": (lambda b: {
            "next_move": b.get("next_move"),
            "autonomous_now": b.get("autonomous_now", []),
            "needs_operator": b.get("needs_operator", []),
            "summary": b.get("summary"),
        } if b else {})(_load(DATA / "orchestrator_brief.json", {})),
        "history": [{"g": h.get("generation"), "m": h.get("mean_score"), "gain": h.get("gain")} for h in hist],
        "recent_improvements": list(reversed(improvements))[:8],
        "top_champions": sorted(
            [{"cls": k, "title": v.get("title", "")[:40], "score": v.get("score", 0),
              "state": v.get("state", "")} for k, v in champs.items()],
            key=lambda x: -x["score"])[:6],
    }
    return out


def main():
    out = build_live_state()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT} — gen {out['generation']} mean {out['mean_score']} state {out['state']} "
          f"live_brain={out['live_brain'].get('live_brain_available')}")


if __name__ == "__main__":
    main()
