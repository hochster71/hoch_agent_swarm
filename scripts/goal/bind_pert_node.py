#!/usr/bin/env python3
"""Bind a PERT node's state to run EVIDENCE. Never hand-editable.

Ratified rule: "The PERT critical path must be generated from unresolved blocking
requirements, not hardcoded status strings." A node's state is DERIVED here from the
most recent council run for that node. If someone hand-edits the node file, re-running
this restores the truth.
"""
import glob, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RELAY = ROOT / "coordination" / "council" / "relay"

node_id = sys.argv[1] if len(sys.argv) > 1 else "H1D"
runs = []
for f in sorted(glob.glob(str(RELAY / "*.council.json"))):
    d = json.loads(Path(f).read_text())
    if d.get("pert_node") == node_id:
        runs.append((d["completed_at"], f, d))
if not runs:
    print(f"no evidence for node {node_id}"); sys.exit(1)

runs.sort()
_, src, d = runs[-1]          # most recent run for this node IS the state
node = {
    "schema": "PERT_NODE_BINDING_v1",
    "pert_node": node_id,
    "title": "Autonomous Council Dispatch and Model Relay",
    "goal": "Remove the founder from routine prompt transport between AI systems.",
    "state": d["pert_node_state"],
    "state_reason": d["pert_node_reason"],
    "state_is_derived": True,
    "binding_rule": ("state is DERIVED from the most recent council run evidence for this node. "
                     "It moves to COMPLETED only when >=2 distinct adapters independently satisfy "
                     "the task evidence contract. A hand-edited string cannot set it -- re-running "
                     "scripts/goal/bind_pert_node.py overwrites any manual edit with the evidence."),
    "evidence_source": str(Path(src).relative_to(ROOT)),
    "accepted_adapters": d["accepted_adapters"],
    "manual_copy_paste_operations": d["manual_copy_paste_operations"],
    "total_cost_usd": d["total_cost_usd"],
    "founder_intervention_required": d["founder_intervention_required"],
    "runs_considered": len(runs),
    "bound_at": d["completed_at"],
}
(RELAY / f"{node_id}_pert_node.json").write_text(json.dumps(node, indent=2) + "\n")
print(f"{node_id}: {node['state']} ({node['state_reason']}) adapters={node['accepted_adapters']} from {len(runs)} runs")
