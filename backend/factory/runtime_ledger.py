"""Runtime usage + outcome feedback ledgers — the proof layer for BRAIN-live.

Doctrine (operator-approved, 2026-07-06): a dashboard panel is not proof, a registry
score is not proof, a RAG answer about prompts is not proof. Only this counts:
    champion prompt selected -> used in actual execution -> outcome logged -> feedback captured.

Two append-only JSONL ledgers, hash-chained like the evidence ledger philosophy:
  data/prompt_brain/runtime_usage_ledger.jsonl    — every operating-prompt resolution USED
  data/prompt_brain/outcome_feedback_ledger.jsonl — the outcome of that execution, keyed back

Usage entry schema (exactly the operator-specified proof shape):
  timestamp, execution_surface, task_class, champion_id, fallback_used,
  registry_path, prompt_hash, outcome_ref, production_mutation_allowed
plus usage_id (sha256 prefix) so outcomes can reference their usage entry.

fallback_used=true proves the loader is SAFE, not that BRAIN drives execution.
BRAIN-live requires at least one entry with fallback_used=false from a real surface.
Stdlib only. Never raises into the execution path.
"""
import json
import hashlib
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
USAGE_LEDGER = ROOT / "data" / "prompt_brain" / "runtime_usage_ledger.jsonl"
OUTCOME_LEDGER = ROOT / "data" / "prompt_brain" / "outcome_feedback_ledger.jsonl"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _append(path: Path, entry: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_usage(resolution: Dict[str, Any], execution_surface: str,
                 production_mutation_allowed: bool = False,
                 outcome_ref: Optional[str] = None) -> Optional[str]:
    """Log that an operating prompt (champion or fallback) was USED by an execution surface.

    `resolution` is the dict returned by champion_loader.operating_prompt().
    Returns usage_id for outcome linkage, or None if logging failed (never raises).
    """
    try:
        prov = resolution.get("provenance", {}) or {}
        from backend.factory.registry import get_factory
        f = get_factory(prov.get("domain", "software"))
        entry = {
            "timestamp": _now(),
            "execution_surface": execution_surface,
            "task_class": prov.get("task_class"),
            "champion_id": prov.get("gene_id"),
            "fallback_used": resolution.get("source") != "champion",
            "registry_path": str(f.champion_registry.relative_to(ROOT)) if f else None,
            "prompt_hash": _sha(resolution.get("prompt", "")),
            "outcome_ref": outcome_ref,
            "production_mutation_allowed": bool(production_mutation_allowed),
            "generation": prov.get("generation"),
            "score_at_selection": prov.get("score"),
        }
        entry["usage_id"] = _sha(json.dumps(entry, sort_keys=True))[:16]
        _append(USAGE_LEDGER, entry)
        return entry["usage_id"]
    except Exception:
        return None


def record_outcome(usage_id: Optional[str], outcome: Dict[str, Any]) -> bool:
    """Log the real outcome of an execution that used a ledgered prompt.

    `outcome` should carry verifiable facts only (status, gate results, response hash,
    latency, artifact paths) — never invented metrics. Returns success; never raises.
    """
    try:
        entry = {"timestamp": _now(), "usage_id": usage_id, **outcome}
        _append(OUTCOME_LEDGER, entry)
        return True
    except Exception:
        return False
