"""Outcome stats — aggregate the runtime + outcome ledgers into per-gene combat records.

Live-real-only doctrine: a champion's registry score says how well its TEXT fits a rubric;
its combat record says what actually happened when it was USED. This module computes the
latter from the two append-only ledgers and writes data/prompt_brain/outcome_stats.json
for the live feed. Read-only over the ledgers; deterministic; stdlib only.

Per gene: executions (champion actually applied), completions, failures, last_used,
surfaces. Per gate stream (live_judge / m0_generation): counts. Nothing here is invented —
every number is a count of ledger lines.
"""
import json
import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent.parent
USAGE = ROOT / "data" / "prompt_brain" / "runtime_usage_ledger.jsonl"
OUTCOME = ROOT / "data" / "prompt_brain" / "outcome_feedback_ledger.jsonl"
OUT = ROOT / "data" / "prompt_brain" / "outcome_stats.json"


def _lines(p: Path):
    if not p.exists():
        return
    with p.open(encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try:
                    yield json.loads(ln)
                except Exception:
                    continue


def compute() -> Dict[str, Any]:
    usage_by_id: Dict[str, Dict] = {}
    genes: Dict[str, Dict[str, Any]] = {}

    for u in _lines(USAGE):
        uid = u.get("usage_id")
        if uid:
            usage_by_id[uid] = u
        if u.get("fallback_used"):
            continue  # only true champion applications count as executions
        gid = u.get("champion_id")
        if not gid:
            continue
        g = genes.setdefault(gid, {"task_class": u.get("task_class"),
                                   "executions": 0, "completed": 0, "failed": 0,
                                   "surfaces": {}, "last_used": None})
        g["executions"] += 1
        g["surfaces"][u.get("execution_surface", "?")] = \
            g["surfaces"].get(u.get("execution_surface", "?"), 0) + 1
        g["last_used"] = max(g["last_used"] or "", u.get("timestamp", ""))

    gates: Dict[str, Dict[str, int]] = {}
    for o in _lines(OUTCOME):
        gate = o.get("gate")
        if gate:
            gs = gates.setdefault(gate, {"total": 0})
            gs["total"] += 1
            st = str(o.get("status", "?"))
            gs[st] = gs.get(st, 0) + 1
            gid = o.get("champion_id")
            if gid and gid in genes:
                genes[gid].setdefault("gate_results", {}).setdefault(gate, 0)
                genes[gid]["gate_results"][gate] += 1
            continue
        uid = o.get("usage_id")
        u = usage_by_id.get(uid) if uid else None
        if not u or u.get("fallback_used"):
            continue
        gid = u.get("champion_id")
        if gid in genes:
            if o.get("status") == "COMPLETED":
                genes[gid]["completed"] += 1
            elif o.get("status") == "FAILED":
                genes[gid]["failed"] += 1

    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return {"schema": "brain-outcome-stats", "at": now,
            "genes_with_combat_record": len(genes),
            "total_champion_executions": sum(g["executions"] for g in genes.values()),
            "genes": genes, "gates": gates}


def write() -> Dict[str, Any]:
    stats = compute()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


if __name__ == "__main__":
    s = write()
    print(f"outcome_stats: {s['genes_with_combat_record']} gene(s) with combat records, "
          f"{s['total_champion_executions']} champion execution(s), "
          f"gates={list(s['gates'].keys())} -> {OUT}")
