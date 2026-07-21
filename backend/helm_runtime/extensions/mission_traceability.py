"""mission_traceability.py — HELM Mission Traceability Graph (Phase 1, EDR-0011).

HELM-GOV | extends: four-engine runtime via composition | edr: EDR-0011
         | why: prove Goal→Requirement→Claim→Evidence chains; detect orphans;
         | observability only — does not drive completion %, prioritization, or promotion.

Composed extension (not frozen core d8d5139a). Deterministic graph_hash over
canonical node+edge serialization. Fail-closed verification helpers.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

EXTENSION_VERSION = "1.0.0"
EXTENSION_EDR = "EDR-0011"
SCHEMA = "HELM_MISSION_TRACE_GRAPH_v1"
SCHEMA_VERSION = "1.0"
GRAPH_HASH_ALGORITHM = "sha256"

# Forbidden for A9/N6: this module must not import Mission Control.
_FORBIDDEN_IMPORT_PREFIX = "backend.mission_control"

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOAL_CONTRACT = ROOT / "config" / "canonical_goal_contract.json"
DEFAULT_REQUIREMENTS = ROOT / "config" / "goal_requirements.json"
DEFAULT_GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"
DEFAULT_GRAPH_PATH = ROOT / "coordination" / "governance" / "mission_trace_graph.json"

# Files Phase 1 must never write (A8).
FORBIDDEN_WRITE_PATHS = frozenset(
    {
        "coordination/goal/executive_mission.json",
        "coordination/goal/mission_state.json",
        "coordination/goal/goal_state.json",
        "config/goal_requirements.json",
        "config/canonical_goal_contract.json",
    }
)


class MissionTraceError(ValueError):
    """Raised on malformed graph structure or duplicate IDs. Fails closed."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_payload(nodes: Sequence[Dict[str, Any]], edges: Sequence[Dict[str, Any]]) -> str:
    """Stable serialization for hashing: sorted nodes by id, edges by (from,to,rel)."""
    def node_key(n: Dict[str, Any]) -> str:
        return str(n.get("id", ""))

    def edge_key(e: Dict[str, Any]) -> Tuple[str, str, str]:
        return (str(e.get("from", "")), str(e.get("to", "")), str(e.get("rel", "")))

    ordered_nodes = sorted((dict(n) for n in nodes), key=node_key)
    ordered_edges = sorted((dict(e) for e in edges), key=edge_key)
    # Drop non-content keys if present
    for n in ordered_nodes:
        n.pop("_tmp", None)
    body = {"nodes": ordered_nodes, "edges": ordered_edges}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_graph_hash(nodes: Sequence[Dict[str, Any]], edges: Sequence[Dict[str, Any]]) -> str:
    """SHA256 of canonical nodes+edges. Pure; deterministic (A6/A7)."""
    payload = _canonical_payload(nodes, edges)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _check_duplicate_ids(nodes: Sequence[Dict[str, Any]]) -> None:
    seen: Dict[str, int] = {}
    for n in nodes:
        nid = str(n.get("id", ""))
        if not nid:
            raise MissionTraceError("node missing id")
        seen[nid] = seen.get(nid, 0) + 1
    dups = [k for k, c in seen.items() if c > 1]
    if dups:
        raise MissionTraceError(f"duplicate node ids: {sorted(dups)}")


def _goal_id_from_contract(contract: Dict[str, Any]) -> str:
    hierarchy = contract.get("goal_hierarchy") or {}
    ns = hierarchy.get("1_canonical_north_star") or {}
    return str(ns.get("id") or "NS")


def _layer_goal_id(layer: str) -> str:
    """Map requirement layer to hierarchy goal/objective id."""
    mapping = {
        "NS": "GOAL-NS",
        "TO": "GOAL-TO",
        "CP": "GOAL-CP",
        "ES": "GOAL-ES",
        "GOV": "GOAL-GOV",
    }
    return mapping.get(layer.upper(), "GOAL-NS")


def build_trace_graph(
    *,
    root: Optional[Path] = None,
    goal_contract_path: Optional[Path] = None,
    requirements_path: Optional[Path] = None,
    goal_state_path: Optional[Path] = None,
    computed_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Seed Goal→Requirement→Claim→Evidence graph from config + optional goal_state.

    Read-only w.r.t. mission/promotion/completion control surfaces (A8).
    Does not import or call Mission Control.
    """
    base = root or ROOT
    gc_path = goal_contract_path or (base / "config" / "canonical_goal_contract.json")
    req_path = requirements_path or (base / "config" / "goal_requirements.json")
    gs_path = goal_state_path or (base / "coordination" / "goal" / "goal_state.json")

    if not gc_path.is_file():
        raise MissionTraceError(f"missing goal contract: {gc_path}")
    if not req_path.is_file():
        raise MissionTraceError(f"missing requirements: {req_path}")

    contract = _load_json(gc_path)
    reqs_doc = _load_json(req_path)
    requirements: List[Dict[str, Any]] = list(reqs_doc.get("requirements") or [])

    goal_state: Optional[Dict[str, Any]] = None
    if gs_path.is_file():
        try:
            goal_state = _load_json(gs_path)
        except (OSError, json.JSONDecodeError):
            goal_state = None

    # Evidence lookup from goal_state requirements list if present
    gs_by_id: Dict[str, Dict[str, Any]] = {}
    if goal_state:
        for r in goal_state.get("requirements") or []:
            if isinstance(r, dict) and r.get("id"):
                gs_by_id[str(r["id"])] = r

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    orphans: List[Dict[str, Any]] = []
    missing_links: List[Dict[str, Any]] = []

    # --- Goals (NS + layer goals) ---
    ns_id = "GOAL-NS"
    nodes.append(
        {
            "id": ns_id,
            "kind": "goal",
            "ref": str(gc_path.relative_to(base)) if _path_under(gc_path, base) else str(gc_path),
            "statement": contract.get("north_star") or "",
            "layer": "NS",
        }
    )
    for lid, label in (
        ("GOAL-TO", "TO"),
        ("GOAL-CP", "CP"),
        ("GOAL-ES", "ES"),
        ("GOAL-GOV", "GOV"),
    ):
        nodes.append(
            {
                "id": lid,
                "kind": "goal",
                "ref": str(gc_path.relative_to(base)) if _path_under(gc_path, base) else str(gc_path),
                "layer": label,
                "parent": ns_id,
            }
        )
        edges.append({"from": lid, "to": ns_id, "rel": "supports"})

    # --- Requirements, Claims, Evidence ---
    if not requirements:
        orphans.append(
            {
                "id": ns_id,
                "kind": "goal",
                "reason": "NO_REQUIREMENT",
            }
        )
        missing_links.append(
            {"from": ns_id, "to_kind": "requirement", "status": "UNKNOWN"}
        )

    for req in requirements:
        rid = str(req.get("id") or "").strip()
        if not rid:
            orphans.append({"id": "(blank)", "kind": "requirement", "reason": "MISSING_ID"})
            continue
        layer = str(req.get("layer") or "NS").upper()
        goal_for_layer = _layer_goal_id(layer)
        statement = str(req.get("statement") or "")

        nodes.append(
            {
                "id": rid,
                "kind": "requirement",
                "ref": str(req_path.relative_to(base)) if _path_under(req_path, base) else str(req_path),
                "layer": layer,
                "statement": statement,
            }
        )
        edges.append({"from": rid, "to": goal_for_layer, "rel": "supports"})
        # Also link NS for path completeness
        if goal_for_layer != ns_id:
            edges.append({"from": rid, "to": ns_id, "rel": "supports_goal"})

        claim_id = f"CLAIM-{rid}"
        nodes.append(
            {
                "id": claim_id,
                "kind": "claim",
                "statement": statement,
                "status": "UNKNOWN",  # refined after evidence
                "requirement_id": rid,
            }
        )
        edges.append({"from": claim_id, "to": rid, "rel": "asserts"})

        # Evidence from requirement config + goal_state overlay
        ev_path = req.get("evidence_path")
        gs_row = gs_by_id.get(rid) or {}
        if gs_row.get("evidence_path"):
            ev_path = gs_row.get("evidence_path")

        presence = "UNKNOWN"
        age_hours: Optional[float] = None
        evidence_exists = None
        if gs_row:
            if "evidence_exists" in gs_row:
                evidence_exists = bool(gs_row["evidence_exists"])
            if gs_row.get("evidence_age_hours") is not None:
                try:
                    age_hours = float(gs_row["evidence_age_hours"])
                except (TypeError, ValueError):
                    age_hours = None

        if ev_path:
            full = base / str(ev_path) if not os.path.isabs(str(ev_path)) else Path(str(ev_path))
            if evidence_exists is True:
                presence = "PRESENT"
            elif evidence_exists is False:
                presence = "MISSING"
            elif full.is_file():
                presence = "PRESENT"
            else:
                presence = "MISSING"
        else:
            presence = "UNKNOWN"
            missing_links.append(
                {"from": claim_id, "to_kind": "evidence", "status": "UNKNOWN"}
            )

        ev_id = f"EV-{rid}"
        nodes.append(
            {
                "id": ev_id,
                "kind": "evidence",
                "path": str(ev_path) if ev_path else None,
                "presence": presence,
                "age_hours": age_hours,
                "claim_id": claim_id,
            }
        )
        edges.append({"from": ev_id, "to": claim_id, "rel": "proves"})

        # Claim status: never PASS without PRESENT evidence (A5)
        if presence == "PRESENT":
            claim_status = "SUPPORTED"
        elif presence == "MISSING":
            claim_status = "UNKNOWN"
            missing_links.append(
                {"from": claim_id, "to_kind": "evidence", "status": "UNKNOWN", "detail": "MISSING"}
            )
        else:
            claim_status = "UNKNOWN"
        # Update claim node status
        for n in nodes:
            if n["id"] == claim_id:
                n["status"] = claim_status
                break

    _check_duplicate_ids(nodes)

    # --- Structural orphan / coverage analysis ---
    by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for n in nodes:
        by_kind.setdefault(str(n["kind"]), []).append(n)

    # A1: every goal has ≥1 requirement via supports edge
    req_ids = {n["id"] for n in by_kind.get("requirement", [])}
    for g in by_kind.get("goal", []):
        gid = g["id"]
        has_req = any(
            e.get("to") == gid and e.get("from") in req_ids and e.get("rel") in ("supports", "supports_goal")
            for e in edges
        )
        # Layer goals may only be linked if that layer has reqs
        layer = g.get("layer")
        if layer and layer != "NS":
            layer_reqs = [n for n in by_kind.get("requirement", []) if n.get("layer") == layer]
            if not layer_reqs:
                # Not an orphan if NS has reqs; optional layer without reqs is OK as empty capability
                continue
        if gid == ns_id and not has_req and not req_ids:
            orphans.append({"id": gid, "kind": "goal", "reason": "NO_REQUIREMENT"})
            missing_links.append({"from": gid, "to_kind": "requirement", "status": "UNKNOWN"})

    # A2: every requirement has ≥1 claim
    claim_for_req = {
        e["to"]: e["from"]
        for e in edges
        if e.get("rel") == "asserts"
    }
    for r in by_kind.get("requirement", []):
        rid = r["id"]
        if rid not in claim_for_req:
            orphans.append({"id": rid, "kind": "requirement", "reason": "NO_CLAIM"})
            missing_links.append({"from": rid, "to_kind": "claim", "status": "UNKNOWN"})

    # A3: every claim has ≥1 evidence edge (even if MISSING/UNKNOWN)
    claims_with_ev = {
        e["to"] for e in edges if e.get("rel") == "proves"
    }
    for c in by_kind.get("claim", []):
        cid = c["id"]
        if cid not in claims_with_ev:
            orphans.append({"id": cid, "kind": "claim", "reason": "NO_EVIDENCE"})
            missing_links.append({"from": cid, "to_kind": "evidence", "status": "UNKNOWN"})

    graph_hash = compute_graph_hash(nodes, edges)

    goals = by_kind.get("goal", [])
    reqs = by_kind.get("requirement", [])
    claims = by_kind.get("claim", [])
    evidence = by_kind.get("evidence", [])

    goals_with_req = 0
    for g in goals:
        if g["id"] != ns_id:
            continue
        if any(e.get("to") == ns_id and e.get("from") in req_ids for e in edges):
            goals_with_req = 1

    requirements_with_claim = sum(1 for r in reqs if r["id"] in claim_for_req)
    claims_with_evidence = sum(1 for c in claims if c["id"] in claims_with_ev)

    # Sort for stable on-disk representation
    nodes_sorted = sorted(nodes, key=lambda n: str(n["id"]))
    edges_sorted = sorted(
        edges, key=lambda e: (str(e.get("from")), str(e.get("to")), str(e.get("rel")))
    )
    orphans_sorted = sorted(orphans, key=lambda o: (str(o.get("kind")), str(o.get("id"))))
    missing_sorted = sorted(
        missing_links,
        key=lambda m: (str(m.get("from")), str(m.get("to_kind")), str(m.get("status"))),
    )

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "graph_hash_algorithm": GRAPH_HASH_ALGORITHM,
        "compatibility": "backward-compatible",
        "extension_version": EXTENSION_VERSION,
        "edr": EXTENSION_EDR,
        "class": "PROJECTION",
        "phase": 1,
        "consumption": "OBSERVE_ONLY",
        "graph_hash": graph_hash,
        "mission_hash": "UNKNOWN",
        "computed_at": computed_at or _now(),
        "nodes": nodes_sorted,
        "edges": edges_sorted,
        "orphans": orphans_sorted,
        "link_status": {
            "missing_links": missing_sorted,
            "note": "Missing links render UNKNOWN, never PASS",
        },
        "coverage": {
            "goals_with_requirement": goals_with_req,
            "requirements_with_claim": requirements_with_claim,
            "claims_with_evidence": claims_with_evidence,
            "orphan_count": len(orphans_sorted),
            "requirement_total": len(reqs),
            "claim_total": len(claims),
            "evidence_total": len(evidence),
        },
    }


def _path_under(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def evaluate_acceptance(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate A1–A5 against a graph dict. Does not mutate graph.

    Returns {criterion: {pass: bool, detail: str}, ..., all_pass: bool}
    """
    results: Dict[str, Any] = {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    orphans = graph.get("orphans") or []
    by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for n in nodes:
        if not isinstance(n, dict):
            continue
        by_kind.setdefault(str(n.get("kind")), []).append(n)

    reqs = by_kind.get("requirement", [])
    claims = by_kind.get("claim", [])
    goals = by_kind.get("goal", [])

    # A1
    ns = next((g for g in goals if g.get("id") == "GOAL-NS"), None)
    req_ids = {r["id"] for r in reqs}
    a1_ok = False
    if ns and req_ids:
        a1_ok = any(
            e.get("to") == "GOAL-NS" and e.get("from") in req_ids for e in edges
        )
    results["A1"] = {
        "pass": a1_ok,
        "detail": "Goal GOAL-NS has ≥1 Requirement" if a1_ok else "GOAL-NS missing Requirement link",
    }

    # A2
    claim_targets = {e.get("to") for e in edges if e.get("rel") == "asserts"}
    missing_claims = [r["id"] for r in reqs if r["id"] not in claim_targets]
    results["A2"] = {
        "pass": len(reqs) > 0 and not missing_claims,
        "detail": "all Requirements have Claims" if not missing_claims else f"missing claims: {missing_claims}",
    }

    # A3
    prove_targets = {e.get("to") for e in edges if e.get("rel") == "proves"}
    missing_ev = [c["id"] for c in claims if c["id"] not in prove_targets]
    results["A3"] = {
        "pass": len(claims) > 0 and not missing_ev,
        "detail": "all Claims have Evidence nodes" if not missing_ev else f"missing evidence: {missing_ev}",
    }

    # A4 — orphans list present and is a list (explicit reporting mechanism)
    results["A4"] = {
        "pass": isinstance(orphans, list),
        "detail": f"orphan_count={len(orphans) if isinstance(orphans, list) else 'INVALID'}",
    }

    # A5 — no claim status may be PASS (we only use SUPPORTED/UNKNOWN/OPEN)
    bad_status = [
        c["id"]
        for c in claims
        if str(c.get("status", "")).upper() in ("PASS", "PASSED", "GREEN")
    ]
    # Also: MISSING evidence must not claim SUPPORTED
    evidence = by_kind.get("evidence", [])
    ev_by_claim = {e.get("claim_id"): e for e in evidence}
    false_supported = []
    for c in claims:
        ev = ev_by_claim.get(c["id"])
        if c.get("status") == "SUPPORTED" and ev and ev.get("presence") != "PRESENT":
            false_supported.append(c["id"])
    a5_ok = not bad_status and not false_supported
    results["A5"] = {
        "pass": a5_ok,
        "detail": "no PASS without PRESENT evidence" if a5_ok else f"bad={bad_status} false_supported={false_supported}",
    }

    # A6/A7 — hash matches recomputation
    try:
        recomputed = compute_graph_hash(nodes, edges)
        stored = graph.get("graph_hash")
        hash_ok = stored == recomputed and isinstance(stored, str) and len(stored) == 64
        results["A6"] = {
            "pass": hash_ok,
            "detail": "graph_hash matches recomputation" if hash_ok else f"stored={stored} recomputed={recomputed}",
        }
        results["A7"] = results["A6"]  # same property; determinism tested separately by double-build
    except Exception as e:
        results["A6"] = {"pass": False, "detail": str(e)}
        results["A7"] = {"pass": False, "detail": str(e)}

    results["all_structural_pass"] = all(
        results[k]["pass"] for k in ("A1", "A2", "A3", "A4", "A5", "A6")
    )
    return results


def validate_graph_structure(graph: Any) -> List[str]:
    """Return list of structural errors. Empty = well-formed."""
    errors: List[str] = []
    if not isinstance(graph, dict):
        return ["graph is not a dict"]
    if graph.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if "nodes" not in graph or not isinstance(graph["nodes"], list):
        errors.append("nodes must be a list")
    if "edges" not in graph or not isinstance(graph["edges"], list):
        errors.append("edges must be a list")
    if "graph_hash" not in graph:
        errors.append("graph_hash missing")
    nodes = graph.get("nodes") or []
    ids: List[str] = []
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            errors.append(f"node[{i}] not a dict")
            continue
        if "id" not in n:
            errors.append(f"node[{i}] missing id")
        else:
            ids.append(str(n["id"]))
    if len(ids) != len(set(ids)):
        errors.append("duplicate node ids")
    return errors


def atomic_write_graph(path: Path, graph: Dict[str, Any]) -> None:
    """Write only the mission trace graph artifact (A8 allowlist)."""
    # Refuse forbidden relative paths
    try:
        rel = str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        rel = str(path)
    if rel in FORBIDDEN_WRITE_PATHS:
        raise MissionTraceError(f"A8 forbidden write path: {rel}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(graph, indent=2, sort_keys=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".mission_trace.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_graph(path: Path) -> Dict[str, Any]:
    """Read-only load helper for future API/dashboard consumers."""
    return _load_json(path)
