"""Recursive Multi-Turn Prompt Optimizer.

Refines prompt candidates over multiple turns by inspecting score breakdowns,
identifying weak rubric dimensions, and prompting the LLM to patch them directly,
subject to the dual-gate LLM judge and mechanical score constraint.
"""
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.brain_convergence.harvest import harvest
from backend.brain_convergence.local_model_bridge import (
    detect_local_backend, _ollama_generate, _lmstudio_generate,
)
from backend.brain_convergence.improve_loop import llm_judge
from backend.brain_convergence.champion import load_registry, save_registry
from backend.factory.registry import get_factory


def get_scorer(domain: str):
    f = get_factory(domain)
    if f:
        return f.scorer()
    from backend.brain_convergence.scorer import score_prompt
    return score_prompt


def recursive_improve_champion(
    champion: Dict[str, Any],
    task_class: str,
    k: int = 3,
    rubric_path: Optional[str] = None,
    backend: Optional[Dict[str, str]] = None,
    domain: str = "software"
) -> Optional[Dict[str, Any]]:
    backend = backend or detect_local_backend()
    if not backend:
        return None

    score_fn = get_scorer(domain)
    current_prompt = champion.get("prompt", "")
    champ_score_res = score_fn(current_prompt, rubric_path)
    current_score = champ_score_res["overall"]

    best_candidate = None
    best_score = current_score
    improved = False

    print(f"Starting recursive optimization for {task_class} (domain={domain}). Base score: {current_score:.2f}")

    for turn in range(1, k + 1):
        score_res = score_fn(current_prompt, rubric_path)
        overall = score_res["overall"]
        dims = score_res.get("dimensions", {})

        weak_dims = {dim: s for dim, s in dims.items() if s < 1.0}
        if not weak_dims:
            print(f"  Turn {turn}: Prompt has achieved perfect score (100.0). Stopping early.")
            break

        weak_str = "\n".join([f"- {dim} (current score: {s:.2f}/1.00)" for dim, s in weak_dims.items()])
        instruction = (
            f"You are recursively optimizing an agent prompt for the task class '{task_class}'.\n"
            f"Here is the current prompt:\n"
            f"---\n{current_prompt}\n---\n\n"
            f"The prompt scored {overall:.2f}/100. It is weak or missing requirements in the following dimensions:\n"
            f"{weak_str}\n\n"
            f"Please rewrite the prompt to specifically strengthen those weak dimensions. Make sure to:\n"
            f"1. Keep all existing scope and constraints.\n"
            f"2. Add precise keywords, clear instructions, output formats, and check validations to satisfy the missing criteria.\n"
            f"3. Return ONLY the complete improved prompt (no comments, no wrapper text)."
        )

        cands = []
        for _ in range(2):
            try:
                if backend["kind"] == "ollama":
                    text = _ollama_generate(backend["base"], backend["model"], instruction, timeout=60.0)
                else:
                    text = _lmstudio_generate(backend["base"], backend["model"], instruction, timeout=60.0)
                if text:
                    cands.append(text)
            except Exception as e:
                print(f"  Turn {turn}: Model call failed: {e}")

        turn_winners = []
        for cand_text in cands:
            cand_score_res = score_fn(cand_text, rubric_path)
            cand_mech = cand_score_res["overall"]
            if cand_mech < overall:
                continue
            judged = llm_judge(backend, current_prompt, cand_text, task_class)
            if judged["winner"] == "B":
                turn_winners.append({
                    "prompt": cand_text,
                    "score": cand_mech,
                    "beats": round(cand_mech - overall, 2),
                    "judge_raw": judged["raw"]
                })

        if turn_winners:
            best_turn = max(turn_winners, key=lambda w: w["score"])
            if best_turn["score"] > best_score:
                current_prompt = best_turn["prompt"]
                best_score = best_turn["score"]
                best_candidate = {
                    "prompt": current_prompt,
                    "source": f"LOCAL:{backend['kind']}:{backend['model']}",
                    "judge": "LOCAL_LLM_JUDGE",
                    "judge_raw": best_turn["judge_raw"],
                    "mech_score": best_score,
                    "beats_mech": round(best_score - current_score, 2),
                    "state": "RECURSIVELY_IMPROVED",
                }
                improved = True
                print(f"  Turn {turn}: Success! Score improved to {best_score:.2f} (+{best_turn['beats']:.2f})")
            else:
                print(f"  Turn {turn}: LLM approved but score did not beat overall best ({best_score:.2f}). Continuing.")
                current_prompt = best_turn["prompt"]
        else:
            print(f"  Turn {turn}: No candidates approved by judge or score regressed. Stopping early.")
            break

    return best_candidate


def run(max_classes: int = 3, k: int = 3):
    ROOT = Path(__file__).resolve().parent.parent.parent
    DATA = ROOT / "data" / "prompt_brain"
    RUBRIC = str(ROOT / "config" / "prompt_score_rubric.yaml")
    LIB = str(ROOT.parent / "hoch_agent_swarm_prompt_library" / "organized" / "promoted" / "hoch_prompt_library_promoted.json")
    ALIASES = str(ROOT.parent / "hoch_agent_swarm_prompt_library" / "organized" / "candidates" / "capability_dedup_aliases.json")

    backend = detect_local_backend()
    if not backend:
        print("recursive_optimizer: no live local model — skipped.")
        return {"skipped": True}

    from backend.brain_convergence.improve_run import _select_classes
    genes = harvest(LIB, aliases_path=ALIASES if Path(ALIASES).exists() else None)["genes"]
    reg = load_registry(str(DATA / "champion_registry.json"))
    champs = reg.get("champions", {})
    ranked = _select_classes(champs, max_classes)

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    wins = []
    for cls, champ in ranked:
        gid = champ.get("gene_id")
        prompt = genes.get(gid, {}).get("prompt") or champ.get("prompt")
        if not prompt:
            continue
        result = recursive_improve_champion({"gene_id": gid, "prompt": prompt, "score": champ.get("score")},
                                           cls, k=k, rubric_path=RUBRIC, backend=backend, domain="software")
        if result:
            new = {
                "gene_id": f"gen-{gid}-{ts[:19].replace(':','').replace('-','')}",
                "title": champ.get("title", "") + " (brain-improved-recursive)",
                "prompt": result["prompt"],
                "score": result["mech_score"],
                "state": "RECURSIVELY_IMPROVED",
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
    print(f"recursive_optimizer: attempted {len(ranked)} classes — "
          f"{len(wins)} improvements promoted: {wins}")
    return {"attempted": len(ranked), "wins": wins, "backend": backend["model"]}


if __name__ == "__main__":
    max_cls = 3
    if len(sys.argv) > 1:
        try:
            max_cls = int(sys.argv[1])
        except ValueError:
            pass
    run(max_cls)
