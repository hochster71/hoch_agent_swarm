"""AI Michael — the HOCH founder orchestrator.

Replicates the cross-factory decision loop the founder runs by hand — the loop repeated all session:

    assess state → find the gap → pick the highest-leverage lever → decide GO/NO-GO on evidence →
    execute the reversible/$0 part → escalate only what needs a human → repeat.

It answers the founder's routine questions (What's the GOAL? What's the gap? What's the next lever?)
from REAL state, and interrupts the human only for T3 calls (money / publish / deploy) or genuine
ambiguity. That is the founder's own rubric dimension `human_loop_reduction` applied to the founder.

DOCTRINE (encoded from the founder's real operating principles, see docs/doctrine + evidence discipline):
    1. No fake-green — a factory reads only what it earned; GO needs evidence.
    2. Evidence before any GO; fail-closed on the unproven.
    3. $0-first — prefer the free local-model / mechanical lever before any spend.
    4. Highest-leverage next — quantity caps quality; unblock the binding constraint first.
    5. Moonshot ambition — always push toward the GOAL, never settle at "good".
    6. T3 needs the operator — money, publish, deploy, secrets never go autonomous.

HONEST BOUNDARY: this PROPOSES actions and classifies them autonomous-vs-escalate; it does not itself
move money, publish, or deploy, and it never fabricates readiness. Deterministic + auditable.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List

from backend.factory.registry import list_factories, get_factory
from backend.brain_convergence import gap_analysis as G

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "prompt_brain" / "orchestrator_brief.json"
LOG = ROOT / "data" / "prompt_brain" / "orchestrator_log.jsonl"

DOCTRINE = [
    "no fake-green — a factory reads only what it earned",
    "evidence before any GO; fail-closed on the unproven",
    "$0-first — free local/mechanical lever before any spend",
    "highest-leverage next — unblock the binding constraint",
    "moonshot ambition — always push toward the GOAL",
    "T3 (money/publish/deploy/secrets) needs the operator",
]

# Per-factory GOAL headline + the frontier action that costs money / needs the founder.
ROADMAP = {
    "software": {"goal": "ship a revenue product while the brain keeps improving",
                 "frontier": ("SHIP", "point HASF at its first real revenue product", "strategic")},
    "music":    {"goal": "original, judged, publishable music across every genre",
                 "frontier": ("RENDER", "stand up audio render + audio-quality judge (M2/M3)", "cost")},
    "research": {"goal": "novel, citation-verified, reproducible research across grand challenges",
                 "frontier": ("EXECUTE", "stand up computational execution + novelty judge (M4/M5)", "cost")},
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _min_pool(domain: str) -> int:
    return 6 if domain == "software" else 3


def _assess(f) -> Dict[str, Any]:
    """One factory: state + gap + the next action the founder would take, classified by tier."""
    gp, reg_p, st_p = f.gene_pool, f.champion_registry, f.convergence_status
    if not Path(gp).exists():
        return {"code": f.code, "domain": f.domain, "state": "EMPTY", "action": "SEED",
                "detail": "no gene pool yet", "cost": "$0", "tier": "AUTONOMOUS",
                "answers": "What's the gap?", "leverage": 5}
    res = G.analyze(str(gp), str(reg_p), str(st_p), min_pool=_min_pool(f.domain), target=70.0)
    reg = json.loads(Path(reg_p).read_text()) if Path(reg_p).exists() else {}
    conv = json.loads(Path(st_p).read_text()) if Path(st_p).exists() else {}
    champs = len(reg.get("champions", {}))
    thin = len(res["thin_classes"])
    need = res["expansion_needed_genes"]
    state = conv.get("state", "SEEDED")
    rm = ROADMAP.get(f.domain, {})

    # The founder's ladder, in priority order.
    if champs == 0 and res["totals"]["total_genes"] > 0:
        act = ("SELECT", "crown champions from the seed pool", "$0", "AUTONOMOUS",
               "What's the next lever?", 9)
    elif thin > 0:
        act = ("EXPAND", f"grow {thin} thin classes (+{need} genes) via the $0 local model",
               "$0", "AUTONOMOUS", "What's the gap?", 8 + min(thin, 6))
    elif state in ("IMPROVING",):
        # improving with full pools → the next real move is the founder-tier frontier
        fr = rm.get("frontier", ("ADVANCE", "advance toward GOAL", "strategic"))
        act = (fr[0], fr[1], "cost/strategic" if fr[2] != "strategic" else "strategic",
               "ESCALATE", "GO on the next milestone?", 6)
    else:
        fr = rm.get("frontier", ("ADVANCE", "advance toward GOAL", "strategic"))
        act = (fr[0], fr[1], fr[2], "ESCALATE", "GO on the next milestone?", 5)

    return {"code": f.code, "domain": f.domain, "goal": rm.get("goal", ""),
            "state": state, "genes": res["totals"]["total_genes"], "champions": champs,
            "thin": thin, "mean": conv.get("mean_score"),
            "action": act[0], "detail": act[1], "cost": act[2], "tier": act[3],
            "answers": act[4], "leverage": act[5]}


def decide() -> Dict[str, Any]:
    assessments = [_assess(f) for f in list_factories()]
    # Rank: autonomous $0 first (do them now), by leverage; escalations after (need the human).
    autonomous = sorted([a for a in assessments if a["tier"] == "AUTONOMOUS"],
                        key=lambda a: -a["leverage"])
    escalate = sorted([a for a in assessments if a["tier"] == "ESCALATE"],
                      key=lambda a: -a["leverage"])
    next_move = autonomous[0] if autonomous else (escalate[0] if escalate else None)

    brief = {
        "schema": "hoch-founder-orchestrator-v1",
        "persona": "AI Michael — all-in-one CEO / founder / builder / SME",
        "at": _now(),
        "doctrine": DOCTRINE,
        "portfolio": assessments,
        "next_move": next_move,
        "autonomous_now": [{"code": a["code"], "action": a["action"], "detail": a["detail"]}
                           for a in autonomous],
        "needs_operator": [{"code": a["code"], "action": a["action"], "detail": a["detail"],
                            "why": f"{a['cost']} · {a['answers']}"} for a in escalate],
        "summary": (f"AI Michael: {len(autonomous)} action(s) I can take now at $0; "
                    f"{len(escalate)} need your founder call (T3/cost)."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(brief, indent=2), encoding="utf-8")
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": brief["at"], "next": next_move and next_move["code"],
                             "autonomous": len(autonomous), "escalate": len(escalate)}) + "\n")
    return brief


if __name__ == "__main__":
    b = decide()
    print(f"AI Michael — founder orchestrator @ {b['at'][:19]}Z")
    print(f"  {b['summary']}")
    nm = b["next_move"]
    if nm:
        print(f"  NEXT MOVE → [{nm['code']}] {nm['action']}: {nm['detail']}  ({nm['tier']}, {nm['cost']})")
    for a in b["needs_operator"]:
        print(f"  NEEDS YOU → [{a['code']}] {a['action']}: {a['detail']}  ({a['why']})")
