#!/usr/bin/env python3
"""Build HELM Mission Traceability Graph (Phase 1, EDR-0011).

Observability only. Writes coordination/governance/mission_trace_graph.json.
Does not modify mission state, goal_state, promotion, or goal_requirements (A8).

Usage:
  python3 scripts/goal/build_mission_trace_graph.py
  python3 scripts/goal/build_mission_trace_graph.py --stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.helm_runtime.extensions.mission_traceability import (  # noqa: E402
    DEFAULT_GRAPH_PATH,
    build_trace_graph,
    atomic_write_graph,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Build Mission Traceability Graph (Phase 1)")
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_GRAPH_PATH,
        help="Output path (default: coordination/governance/mission_trace_graph.json)",
    )
    p.add_argument("--stdout", action="store_true", help="Print graph JSON to stdout")
    p.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    args = p.parse_args()

    graph = build_trace_graph(root=args.root)
    if not args.stdout:
        atomic_write_graph(args.out, graph)
        print(f"wrote: {args.out}")
        print(f"graph_hash: {graph['graph_hash']}")
        print(f"coverage: {json.dumps(graph['coverage'])}")
        print(f"orphans: {graph['coverage']['orphan_count']}")
        print(f"consumption: {graph['consumption']}")
    else:
        print(json.dumps(graph, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
