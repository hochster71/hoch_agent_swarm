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


def _select_classes(champs: dict, max_classes: int):
    """Weakest-priority + rotating coverage. Returns list of (class, champ) pairs.

    Half the budget = the lowest-scoring champions (biggest gains). The other half advances a
    persisted round-robin cursor over the full class list, so classes in the middle of the pack
    are eventually revisited instead of never being touched. Deterministic given the cursor file.
    """
    from pathlib import Path as _P
    items = sorted(champs.items(), key=lambda kv: kv[1].get("score", 0.0))
    if max_classes >= len(items):
        return items
    n_weak = max(1, max_classes // 2)
    weak = items[:n_weak]
    weak_keys = {k for k, _ in weak}

    rotating = [it for it in items if it[0] not in weak_keys]
    cur_path = _P(__file__).resolve().parent.parent.parent / "data" / "prompt_brain" / "improve_cursor.json"
    cursor = 0
    try:
        cursor = json.loads(cur_path.read_text()).get("cursor", 0)
    except Exception:
        cursor = 0
    n_rot = max_classes - len(weak)
    picked = []
    if rotating and n_rot > 0:
        for i in range(n_rot):
            picked.append(rotating[(cursor + i) % len(rotating)])
        cursor = (cursor + n_rot) % len(rotating)
        try:
            cur_path.parent.mkdir(parents=True, exist_ok=True)
            cur_path.write_text(json.dumps({"cursor": cursor}))
        except Exception:
            pass
    return weak + picked


def run(max_classes: int = 3):
    backend = detect_local_backend()
    if not backend:
        print("improve_run: no live local model — skipped (start Ollama to enable). Mechanical loop unaffected.")
        return {"skipped": True}

    genes = harvest(LIB, aliases_path=ALIASES if Path(ALIASES).exists() else None)["genes"]
    reg = load_registry(str(DATA / "champion_registry.json"))
    champs = reg.get("champions", {})
    # Coverage-aware selection: half the budget goes to the WEAKEST champions (most room to
    # improve), the other half rotates through ALL classes via a persisted cursor so every class
    # gets worked over successive cycles — 'all areas', not just the perpetual bottom-3.
    ranked = _select_classes(champs, max_classes)

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
