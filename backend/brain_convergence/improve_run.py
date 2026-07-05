"""One self-improvement pass over the champion registry using the live local brain.

For the lowest-scoring champions, ask the brain (improve_loop, dual-gated) to beat them. Genuine
wins are recorded to the champion registry (with the improved prompt + provenance) and appended to
data/prompt_brain/improved_champions.jsonl. If no local model is up, it skips cleanly (mechanical
run_m0 still runs the selection side). Meant to be called by brain_cadence.sh each cycle.

    python3 -m backend.brain_convergence.improve_run [max_classes]
"""
import sys
import json
import datetime
from pathlib import Path

from backend.brain_convergence.harvest import harvest
from backend.brain_convergence.local_model_bridge import detect_local_backend
from backend.brain_convergence.improve_loop import improve_champion
from backend.brain_convergence.champion import load_registry, save_registry

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "prompt_brain"
RUBRIC = str(ROOT / "config" / "prompt_score_rubric.yaml")
LIB = str(ROOT.parent / "hoch_agent_swarm_prompt_library" / "organized" / "promoted" / "hoch_prompt_library_promoted.json")
ALIASES = str(ROOT.parent / "hoch_agent_swarm_prompt_library" / "organized" / "candidates" / "capability_dedup_aliases.json")


def run(max_classes: int = 3):
    backend = detect_local_backend()
    if not backend:
        print("improve_run: no live local model — skipped (start Ollama to enable). Mechanical loop unaffected.")
        return {"skipped": True}

    genes = harvest(LIB, aliases_path=ALIASES if Path(ALIASES).exists() else None)["genes"]
    reg = load_registry(str(DATA / "champion_registry.json"))
    champs = reg.get("champions", {})
    # target the lowest-scoring champions — most room to improve
    ranked = sorted(champs.items(), key=lambda kv: kv[1].get("score", 0.0))[:max_classes]

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    wins = []
    for cls, champ in ranked:
        gid = champ.get("gene_id")
        prompt = genes.get(gid, {}).get("prompt") or champ.get("prompt")
        if not prompt:
            continue
        result = improve_champion({"gene_id": gid, "prompt": prompt, "score": champ.get("score")},
                                  cls, n=1, rubric_path=RUBRIC, backend=backend)
        if result:
            new = {
                "gene_id": f"gen-{gid}-{ts[:19].replace(':','').replace('-','')}",
                "title": champ.get("title", "") + " (brain-improved)",
                "prompt": result["prompt"],
                "score": result["mech_score"],
                "state": "GENERATED_AND_JUDGED",
                "improved_from": gid,
                "source": result["source"],
                "judge": result["judge"],
                "beats_mech": result["beats_mech"],
                "at": ts,
            }
            champs[cls] = new
            wins.append((cls, result["beats_mech"]))
            with open(DATA / "improved_champions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"task_class": cls, **new}) + "\n")

    if wins:
        save_registry(reg, str(DATA / "champion_registry.json"))
    print(f"improve_run: attempted {len(ranked)} classes via {backend['model']} — "
          f"{len(wins)} genuine improvements promoted: {wins}")
    return {"attempted": len(ranked), "wins": wins, "backend": backend["model"]}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run(n)
