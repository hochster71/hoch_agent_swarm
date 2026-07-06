"""BRAIN research meta-loop — the self-directing lever picker.

Each cycle this reads the REAL gap analysis + convergence state + live-model status and decides the
single highest-leverage action, in priority order:

  IMPROVER_OFFLINE  no local model up -> only mechanical SELECT is possible; recommend starting it
  EXPAND            thin pools exist (and model up) -> grow quantity first (it caps quality)
  SELECT            classes have genes but no champion -> run selection to crown them
  IMPROVE           adequate pools but champions below target -> best-of-N quality lever
  RECONCILE         only taxonomy drift remains -> recommend merges (operator-confirmed, never auto)
  HOLD/CONVERGED    online + every class saturated + convergence plateaued -> honestly can't get
                    smarter with the current levers (this is the ONLY path to a 'done for now' claim)

This is 'research and do it again until we can't get smarter', made explicit and auditable. It
decides; the cadence script executes the chosen lever. It writes a decision record (JSON + append
log) the console can show. No fabrication: 'global_converged' is true only under the strict online
+ saturated + plateaued conjunction — never while blind or while any lever still has headroom.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any

from backend.brain_convergence import gap_analysis

ROOT = Path(__file__).resolve().parent.parent.parent
D = ROOT / "data" / "prompt_brain"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def decide() -> Dict[str, Any]:
    try:
        from backend.brain_convergence.local_model_bridge import detect_local_backend
        backend = detect_local_backend()
    except Exception:
        backend = None
    online = bool(backend)

    res = gap_analysis.analyze(str(D / "gene_pool_m0.json"),
                               str(D / "champion_registry.json"),
                               str(D / "convergence_status.json"))
    conv = {}
    try:
        conv = json.loads((D / "convergence_status.json").read_text())
    except Exception:
        pass

    bc = res["by_constraint"]
    thin = res["thin_classes"]
    lowc = res["low_ceiling_classes"]
    no_champ = [r for r in res["per_class"] if r["constraint"] == "NO_CHAMPION"]
    drift = res["taxonomy_drift"]

    # Priority ladder.
    if not online:
        lever, reason, targets = ("IMPROVER_OFFLINE",
            "No local model reachable — only mechanical SELECT can run. Start Ollama to enable "
            "EXPAND/IMPROVE (the $0 generate path).", [])
    elif thin:
        lever, reason = "EXPAND", (f"{len(thin)} thin pools cap champion quality; "
                                   f"need {res['expansion_needed_genes']} synthetic genes.")
        targets = [r["class"] for r in thin]
    elif no_champ:
        lever, reason = "SELECT", f"{len(no_champ)} classes have genes but no champion — crown them."
        targets = [r["class"] for r in no_champ]
    elif lowc:
        lever, reason = "IMPROVE", f"{len(lowc)} champions below target with adequate pools — best-of-N."
        targets = [r["class"] for r in lowc]
    elif drift:
        lever, reason = "RECONCILE", f"{len(drift)} taxonomy-drift pairs remain — recommend merges."
        targets = [f"{d['a']} ⇄ {d['b']}" for d in drift]
    else:
        lever, reason, targets = "HOLD", "Every class saturated.", []

    # Honest global-converged: online AND no headroom lever remains AND convergence plateaued.
    global_converged = bool(
        online and not thin and not no_champ and not lowc
        and conv.get("converged") is True and conv.get("state") == "CONVERGED"
    )
    if global_converged:
        lever = "CONVERGED"
        reason = ("Online, every class saturated, and the mean has plateaued below epsilon for the "
                  "patience window — honestly at the ceiling of the current levers.")

    decision = {
        "schema": "brain-research-meta-v1",
        "at": _now(),
        "improver_online": online,
        "model": (backend or {}).get("model"),
        "chosen_lever": lever,
        "reason": reason,
        "targets": targets[:12],
        "gaps": {
            "by_constraint": bc,
            "thin": len(thin),
            "low_ceiling": len(lowc),
            "no_champion": len(no_champ),
            "drift": len(drift),
            "expansion_needed_genes": res["expansion_needed_genes"],
            "mean_champion_score": res["totals"]["mean_champion_score"],
            "generation": res["totals"]["generation"],
        },
        "global_converged": global_converged,
    }
    D.mkdir(parents=True, exist_ok=True)
    (D / "research_meta_decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    with open(D / "research_meta_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({k: decision[k] for k in ("at", "chosen_lever", "reason", "gaps",
                                                      "improver_online", "global_converged")}) + "\n")
    return decision


if __name__ == "__main__":
    d = decide()
    print(f"meta: lever={d['chosen_lever']} | online={d['improver_online']} | "
          f"gen={d['gaps']['generation']} mean={d['gaps']['mean_champion_score']} | "
          f"thin={d['gaps']['thin']} low={d['gaps']['low_ceiling']} drift={d['gaps']['drift']} | "
          f"global_converged={d['global_converged']}")
    print(f"   reason: {d['reason']}")
    if d["targets"]:
        print(f"   targets: {', '.join(str(t) for t in d['targets'][:8])}")
