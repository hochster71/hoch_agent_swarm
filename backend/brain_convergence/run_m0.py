"""M0 BRAIN Convergence — one-generation orchestrator.

Runs the full mechanical loop for one generation and writes evidence:
  harvest -> splits (held-out) -> AUDIT GATE -> score held-out -> promote champions -> convergence.

Fail-closed: if the seeded-fault scorer audit fails, the run ABORTS and promotes nothing — a
broken evaluator must never crown a champion. Deterministic, no network, no live LLM: safe to
run every burn-in cycle at Rung 1.

    python3 -m backend.brain_convergence.run_m0 [library.json] [aliases.json]
"""
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from backend.brain_convergence.harvest import harvest
from backend.brain_convergence.splits import make_splits, assert_disjoint, write_splits
from backend.brain_convergence.scorer import score_prompt
from backend.brain_convergence.judge_audit import audit_scorer
from backend.brain_convergence.champion import load_registry, promote, mean_champion_score, save_registry
from backend.brain_convergence.convergence import update as conv_update

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "prompt_brain"
EVID = ROOT / "docs" / "evidence" / "moonshot"
RUBRIC = str(ROOT / "config" / "prompt_score_rubric.yaml")

DEFAULT_LIB = str(ROOT.parent / "hoch_agent_swarm_prompt_library" / "organized" / "promoted" / "hoch_prompt_library_promoted.json")
DEFAULT_ALIASES = str(ROOT.parent / "hoch_agent_swarm_prompt_library" / "organized" / "candidates" / "capability_dedup_aliases.json")


def run(library_path: str, aliases_path: Optional[str] = None) -> Dict[str, Any]:
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    h = harvest(library_path, aliases_path=aliases_path)
    s = make_splits(h["by_class"])
    assert_disjoint(s)  # raises on leakage
    write_splits(s, str(DATA / "splits_m0.json"))

    # AUDIT GATE — fail-closed
    audit = audit_scorer(rubric_path=RUBRIC)
    if not audit["passed"]:
        return {"status": "BLOCKED", "reason": audit["verdict"], "audit": audit}

    heldout = set(s["heldout"])
    candidates: Dict[str, Dict[str, Any]] = {}
    for cls, gids in h["by_class"].items():
        ho = [g for g in gids if g in heldout and g in h["genes"]]
        if not ho:
            continue
        scored = [(g, score_prompt(h["genes"][g]["prompt"], RUBRIC)["overall"]) for g in ho]
        best_g, best_s = max(scored, key=lambda x: x[1])
        candidates[cls] = {"gene_id": best_g, "title": h["genes"][best_g]["title"], "score": best_s}

    reg = load_registry(str(DATA / "champion_registry.json"))
    res = promote(reg, candidates, s["provenance_hash"])
    save_registry(res["registry"], str(DATA / "champion_registry.json"))
    mean = mean_champion_score(res["registry"])
    # Pass the REAL improver status so convergence can't fake-green while the model is offline.
    try:
        from backend.brain_convergence.local_model_bridge import detect_local_backend
        improver_online = bool(detect_local_backend())
    except Exception:
        improver_online = False
    conv = conv_update(str(DATA / "convergence_status.json"), res["registry"]["generation"], mean,
                       improver_online=improver_online)

    EVID.mkdir(parents=True, exist_ok=True)
    stamp = ts.replace(":", "").replace("-", "")
    evid_path = EVID / f"M0_GEN_{stamp}.md"
    evid_path.write_text(
        f"# M0 Convergence Generation {res['registry']['generation']}\n\n"
        f"* Captured: {ts}\n* Library: {library_path}\n* Scorer: MECHANICAL_PROXY (Rung 1)\n\n"
        f"- Genes: {h['count']} across {h['task_classes']} classes (collapsed {h['collapsed']} dupes)\n"
        f"- Splits: train {len(s['train'])} / dev {len(s['dev'])} / held-out {len(s['heldout'])} · disjoint ✓\n"
        f"- Scorer audit: {audit['verdict']} (bad={audit['known_bad_score']}, good={audit['known_good_score']})\n"
        f"- Champions promoted this gen: {len(res['promoted'])} · held: {len(res['held'])}\n"
        f"- Mean champion score: {mean} · convergence state: {conv['state']}"
        f"{' (last gain '+str(conv['last_gain'])+')' if conv['last_gain'] is not None else ''}\n"
        f"- Split provenance: `{s['provenance_hash'][:16]}`\n", encoding="utf-8")

    return {
        "status": "VERIFIED", "generation": res["registry"]["generation"],
        "genes": h["count"], "heldout": len(s["heldout"]),
        "promoted": len(res["promoted"]), "held": len(res["held"]),
        "mean_champion_score": mean, "convergence": conv["state"],
        "evidence": str(evid_path),
    }


def main():
    lib = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LIB
    aliases = sys.argv[2] if len(sys.argv) > 2 else (DEFAULT_ALIASES if Path(DEFAULT_ALIASES).exists() else None)
    r = run(lib, aliases)
    print(json.dumps(r, indent=2))
    # Gate-outcome piping (2026-07-06): each generation's verification is a real
    # mechanical gate result — ledger it alongside execution outcomes.
    try:
        from backend.factory.runtime_ledger import record_outcome
        record_outcome(None, {"gate": "m0_generation", "execution_surface": "run_m0",
                              "status": r.get("status"), "generation": r.get("generation"),
                              "promoted": r.get("promoted"),
                              "mean_champion_score": r.get("mean_champion_score"),
                              "convergence": r.get("convergence"),
                              "evidence": r.get("evidence")})
    except Exception:
        pass
    print(f"\nSTATUS={r['status']} | gen={r.get('generation')} | promoted={r.get('promoted')} "
          f"| mean={r.get('mean_champion_score')} | {r.get('convergence')} | evidence={r.get('evidence')}")
    sys.exit(0 if r["status"] == "VERIFIED" else 1)


if __name__ == "__main__":
    main()
