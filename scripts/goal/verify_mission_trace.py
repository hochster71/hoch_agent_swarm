#!/usr/bin/env python3
"""Standalone Mission Traceability Graph verifier (Phase 1, EDR-0011).

A9: does NOT import backend.mission_control.
Not registered in goal_requirements.json (non-consumption rule).

Usage:
  python3 scripts/goal/verify_mission_trace.py
  python3 scripts/goal/verify_mission_trace.py --graph path/to/graph.json
  python3 scripts/goal/verify_mission_trace.py --rebuild-check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import ONLY the extension + stdlib (A9). No mission_control.
from backend.helm_runtime.extensions.mission_traceability import (  # noqa: E402
    DEFAULT_GRAPH_PATH,
    SCHEMA,
    build_trace_graph,
    compute_graph_hash,
    evaluate_acceptance,
    validate_graph_structure,
)


def _assert_no_mission_control_imported() -> None:
    bad = [m for m in sys.modules if m == "backend.mission_control" or m.startswith("backend.mission_control.")]
    if bad:
        raise RuntimeError(f"A9 violation: mission_control imported: {bad}")


def verify(
    *,
    graph_path: Path,
    root: Path,
    rebuild_check: bool,
) -> int:
    _assert_no_mission_control_imported()

    if not graph_path.is_file():
        print(f"FAIL: graph missing: {graph_path}")
        print("graph_status=MISSING")
        return 1

    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: malformed graph: {e}")
        return 1

    errors = validate_graph_structure(graph)
    if errors:
        print("FAIL: structural errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    # Hash integrity (N5 / A6)
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    recomputed = compute_graph_hash(nodes, edges)
    stored = graph.get("graph_hash")
    if stored != recomputed:
        print("FAIL: graph_hash mismatch (tamper or non-canonical store)")
        print(f"  stored:     {stored}")
        print(f"  recomputed: {recomputed}")
        return 1

    acceptance = evaluate_acceptance(graph)
    failed = [k for k in ("A1", "A2", "A3", "A4", "A5", "A6") if not acceptance[k]["pass"]]
    for k in ("A1", "A2", "A3", "A4", "A5", "A6"):
        status = "PASS" if acceptance[k]["pass"] else "FAIL"
        print(f"  {k}: {status} — {acceptance[k]['detail']}")

    if rebuild_check:
        rebuilt = build_trace_graph(root=root)
        if rebuilt["graph_hash"] != stored:
            print("FAIL: rebuild hash differs from on-disk graph (sources changed or non-determinism)")
            print(f"  disk:    {stored}")
            print(f"  rebuild: {rebuilt['graph_hash']}")
            return 1
        print("  rebuild_check: PASS — identical graph_hash")

    _assert_no_mission_control_imported()

    if failed:
        print(f"FAIL: criteria failed: {failed}")
        return 1

    print("PASS: Mission Traceability Graph verification")
    print(f"  schema: {graph.get('schema')}")
    print(f"  graph_hash: {stored}")
    print(f"  orphan_count: {(graph.get('coverage') or {}).get('orphan_count')}")
    print(f"  consumption: {graph.get('consumption')}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Verify Mission Traceability Graph (standalone)")
    p.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument(
        "--rebuild-check",
        action="store_true",
        help="Also rebuild from sources and require identical graph_hash",
    )
    args = p.parse_args()
    return verify(graph_path=args.graph, root=args.root, rebuild_check=args.rebuild_check)


if __name__ == "__main__":
    raise SystemExit(main())
