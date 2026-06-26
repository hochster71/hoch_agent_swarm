import sqlite3
import json
import uuid
from datetime import datetime, timezone
from backend.hochster_cluster import DB_PATH
from backend.runtime_execution_store import apply_pragmas, get_evidence_graph_links, persist_evidence_graph_link, delete_evidence_graph_link

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    return conn

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_evidence_graph() -> dict:
    conn = get_db_connection()
    nodes = {}
    edges = []

    # Helper to add node if not exists
    def add_node(graph_id: str, node_type: str, label: str, properties: dict = None, missing: bool = False):
        if graph_id not in nodes:
            nodes[graph_id] = {
                "id": graph_id,
                "type": node_type,
                "label": label,
                "properties": properties or {},
                "missing": missing
            }

    # Helper to add edge
    def add_edge(source: str, target: str, rel_type: str):
        # Prevent exact duplicate edges in list
        for edge in edges:
            if edge["source"] == source and edge["target"] == target and edge["type"] == rel_type:
                return
        edges.append({
            "source": source,
            "target": target,
            "type": rel_type
        })

    try:
        # 1. Swarm Runs
        for row in conn.execute("SELECT * FROM swarm_runs").fetchall():
            run_id = row["run_id"]
            graph_id = f"run:{run_id}"
            add_node(graph_id, "run", f"Run: {row['name']}", {
                "run_id": run_id,
                "status": row["status"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
                "score": row["score"]
            })

        # 2. Swarm Agents
        for row in conn.execute("SELECT * FROM swarm_agents").fetchall():
            agent_id = row["agent_id"]
            graph_id = f"agent:{agent_id}"
            add_node(graph_id, "agent", f"Agent: {row['display_name']}", {
                "agent_id": agent_id,
                "title": row["title"],
                "tag": row["tag"],
                "system_role": row["system_role"],
                "status": row["status"],
                "tier": row["tier"]
            })

        # 3. Swarm Tasks
        for row in conn.execute("SELECT * FROM swarm_tasks").fetchall():
            task_id = row["task_id"]
            run_id = row["run_id"]
            graph_id = f"task:{run_id}:{task_id}"
            add_node(graph_id, "task", f"Task: {row['title']}", {
                "task_id": task_id,
                "run_id": run_id,
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "risk_level": row["risk_level"],
                "approval_required": bool(row["approval_required"])
            })
            # Edges
            add_edge(graph_id, f"run:{run_id}", "belongs_to")
            if row["owner_agent_id"]:
                add_edge(graph_id, f"agent:{row['owner_agent_id']}", "executed_by")

        # 4. Swarm Artifacts
        for row in conn.execute("SELECT * FROM swarm_artifacts").fetchall():
            art_id = row["artifact_id"]
            graph_id = f"artifact:{art_id}"
            add_node(graph_id, "artifact", f"Artifact: {row['name']}", {
                "artifact_id": art_id,
                "path": row["path"],
                "hash": row["hash"],
                "status": row["status"],
                "created_at": row["created_at"],
                "mime_type": row["mime_type"],
                "evidence_type": row["evidence_type"],
                "signature_status": row["signature_status"]
            })
            # Edges
            if row["task_id"] and row["run_id"]:
                add_edge(graph_id, f"task:{row['run_id']}:{row['task_id']}", "produced_by")
            elif row["run_id"]:
                add_edge(graph_id, f"run:{row['run_id']}", "associated_with")
            
            if row["created_by_agent_id"]:
                add_edge(graph_id, f"agent:{row['created_by_agent_id']}", "signed_by")

        # 5. Approval Gates
        for row in conn.execute("SELECT * FROM hochster_approval_gates").fetchall():
            app_id = row["approval_id"]
            graph_id = f"approval:{app_id}"
            add_node(graph_id, "approval", f"Approval Gate ({row['action_type']})", {
                "approval_id": app_id,
                "request_id": row["request_id"],
                "correlation_id": row["correlation_id"],
                "risk_level": row["risk_level"],
                "status": row["status"],
                "requested_by": row["requested_by"],
                "created_at": row["created_at"]
            })
            # Edges: Try to link to matching Task/Run via request_id or correlation_id
            req_id = row["request_id"]
            corr_id = row["correlation_id"]
            
            # Look up run or task matching the request_id/correlation_id
            linked = False
            for node_id in nodes:
                if node_id.startswith("task:"):
                    # node_id = task:run_id:task_id
                    parts = node_id.split(":")
                    if len(parts) == 3:
                        if parts[2] == req_id or parts[2] == corr_id:
                            add_edge(graph_id, node_id, "guards_task")
                            linked = True
                elif node_id.startswith("run:"):
                    parts = node_id.split(":")
                    if len(parts) == 2:
                        if parts[1] == req_id or parts[1] == corr_id:
                            add_edge(graph_id, node_id, "guards_run")
                            linked = True
            
            # Default link back to run or task
            if not linked:
                if corr_id and corr_id.startswith("corr-"):
                    pass # Historical or external trace

        # 6. Candidate Packets
        for row in conn.execute("SELECT * FROM candidate_release_packets").fetchall():
            cp_id = row["candidate_packet_id"]
            graph_id = f"candidate:{cp_id}"
            add_node(graph_id, "candidate", f"Candidate Packet v{row['candidate_version']}", {
                "candidate_packet_id": cp_id,
                "candidate_version": row["candidate_version"],
                "candidate_channel": row["candidate_channel"],
                "created_at": row["created_at"],
                "head_sha": row["head_sha"],
                "branch": row["branch"],
                "qa_status": row["qa_status"],
                "packet_status": row["packet_status"],
                "formal_release_ready": bool(row["formal_release_ready"])
            })
            # Edges
            if row["operator_decision_id"]:
                add_edge(graph_id, f"approval:{row['operator_decision_id']}", "approved_by")
            
            # Included artifacts
            try:
                included = json.loads(row["included_artifacts_json"])
                for art in included:
                    if isinstance(art, dict) and "id" in art:
                        add_edge(graph_id, f"artifact:{art['id']}", "includes")
                    elif isinstance(art, str):
                        add_edge(graph_id, f"artifact:{art}", "includes")
            except Exception:
                pass

            # Missing artifacts
            try:
                missing = json.loads(row["missing_artifacts_json"])
                for art in missing:
                    art_id = art.get("id") if isinstance(art, dict) else art
                    if art_id:
                        missing_graph_id = f"artifact:{art_id}"
                        add_node(missing_graph_id, "artifact", f"Missing Artifact: {art_id}", {"missing": True}, missing=True)
                        add_edge(graph_id, missing_graph_id, "missing_evidence")
            except Exception:
                pass

        # 7. Formal Previews
        for row in conn.execute("SELECT * FROM formal_release_previews").fetchall():
            fp_id = row["formal_preview_id"]
            graph_id = f"formal_preview:{fp_id}"
            add_node(graph_id, "formal_preview", f"Formal Preview v{row['candidate_version']}", {
                "formal_preview_id": fp_id,
                "candidate_packet_id": row["candidate_packet_id"],
                "candidate_version": row["candidate_version"],
                "created_at": row["created_at"],
                "head_sha": row["head_sha"],
                "release_tag": row["release_tag"],
                "tag_status": row["tag_status"],
                "formal_release_ready": bool(row["formal_release_ready"]),
                "preview_status": row["preview_status"]
            })
            # Edges
            add_edge(graph_id, f"candidate:{row['candidate_packet_id']}", "previews")

        # 8. Seal Dry Runs
        for row in conn.execute("SELECT * FROM formal_release_seal_dry_runs").fetchall():
            sd_id = row["seal_dry_run_id"]
            graph_id = f"seal_dry_run:{sd_id}"
            add_node(graph_id, "seal_dry_run", f"Seal Dry Run", {
                "seal_dry_run_id": sd_id,
                "formal_preview_id": row["formal_preview_id"],
                "candidate_packet_id": row["candidate_packet_id"],
                "created_at": row["created_at"],
                "operator": row["operator"],
                "head_sha": row["head_sha"],
                "release_tag": row["release_tag"],
                "seal_status": row["seal_status"]
            })
            # Edges
            add_edge(graph_id, f"formal_preview:{row['formal_preview_id']}", "seals")
            add_edge(graph_id, f"candidate:{row['candidate_packet_id']}", "targets_candidate")

        # 9. Attestation Bundles
        for row in conn.execute("SELECT * FROM release_seal_attestation_bundles").fetchall():
            ab_id = row["attestation_bundle_id"]
            graph_id = f"attestation:{ab_id}"
            add_node(graph_id, "attestation", f"Attestation Bundle", {
                "attestation_bundle_id": ab_id,
                "seal_dry_run_id": row["seal_dry_run_id"],
                "created_at": row["created_at"],
                "created_by_operator": row["created_by_operator"],
                "release_tag": row["release_tag"],
                "attestation_status": row["attestation_status"],
                "formal_release_ready": bool(row["formal_release_ready"]),
                "no_mutation_guarantee": bool(row["no_mutation_guarantee"])
            })
            # Edges
            if row["seal_dry_run_id"]:
                add_edge(graph_id, f"seal_dry_run:{row['seal_dry_run_id']}", "attests")
            if row["formal_preview_id"]:
                add_edge(graph_id, f"formal_preview:{row['formal_preview_id']}", "attests_preview")
            if row["candidate_packet_id"]:
                add_edge(graph_id, f"candidate:{row['candidate_packet_id']}", "attests_candidate")
            
            try:
                included = json.loads(row["included_artifacts_json"])
                for art in included:
                    if isinstance(art, dict) and "id" in art:
                        add_edge(graph_id, f"artifact:{art['id']}", "attests_artifact")
                    elif isinstance(art, str):
                        add_edge(graph_id, f"artifact:{art}", "attests_artifact")
            except Exception:
                pass

            try:
                missing = json.loads(row["missing_artifacts_json"])
                for art in missing:
                    art_id = art.get("id") if isinstance(art, dict) else art
                    if art_id:
                        missing_graph_id = f"artifact:{art_id}"
                        add_node(missing_graph_id, "artifact", f"Missing Attested Artifact: {art_id}", {"missing": True}, missing=True)
                        add_edge(graph_id, missing_graph_id, "missing_evidence")
            except Exception:
                pass

        # 10. Service Node / Devices
        for row in conn.execute("SELECT * FROM device_service_registry").fetchall():
            node_id = row["node_id"]
            graph_id = f"device:{node_id}"
            add_node(graph_id, "device", f"Device: {row['display_name']}", {
                "node_id": node_id,
                "device_class": row["device_class"],
                "fleet_group": row["fleet_group"],
                "compute_tier": row["compute_tier"],
                "last_seen": row["last_seen"],
                "health_status": row["health_status"]
            })

        # 11. Model Providers
        for row in conn.execute("SELECT * FROM model_providers").fetchall():
            mp_id = row["model_provider_id"]
            graph_id = f"model_provider:{mp_id}"
            add_node(graph_id, "model_provider", f"Provider: {row['display_name']}", {
                "model_provider_id": mp_id,
                "provider_type": row["provider_type"],
                "health_status": row["health_status"],
                "default_model": row["default_model"],
                "latency_ms": row["latency_ms"]
            })
            # Link to hosting device
            if row["node_id"]:
                add_edge(graph_id, f"device:{row['node_id']}", "hosted_on")

        # 12. Inference Runs
        for row in conn.execute("SELECT * FROM inference_runs").fetchall():
            inf_id = row["inference_run_id"]
            graph_id = f"inference:{inf_id}"
            model_id = row["model_id"]
            add_node(graph_id, "inference", f"Inference ({model_id})", {
                "inference_run_id": inf_id,
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
                "model_id": model_id,
                "status": row["status"],
                "latency_ms": row["latency_ms"],
                "prompt_hash": row["prompt_hash"],
                "response_hash": row["response_hash"]
            })
            # Edges
            if row["task_id"]:
                # Try to find corresponding task graph id
                for t_id in nodes:
                    if t_id.startswith("task:") and t_id.endswith(f":{row['task_id']}"):
                        add_edge(graph_id, t_id, "belongs_to")
            if row["agent_id"]:
                add_edge(graph_id, f"agent:{row['agent_id']}", "invoked_by")
            if row["node_id"]:
                add_edge(graph_id, f"device:{row['node_id']}", "runs_on")
            if row["model_provider_id"]:
                add_edge(graph_id, f"model_provider:{row['model_provider_id']}", "served_by")
            
            # Virtual model node
            model_graph_id = f"model:{model_id}"
            add_node(model_graph_id, "model", f"Model: {model_id}", {"model_id": model_id})
            add_edge(graph_id, model_graph_id, "utilizes")

        # 13. Swarm Routing History
        for row in conn.execute("SELECT * FROM swarm_routing_history").fetchall():
            rt_id = row["routing_id"]
            graph_id = f"routing:{rt_id}"
            add_node(graph_id, "routing", f"Routing: {row['task_type']}", {
                "routing_id": rt_id,
                "task_type": row["task_type"],
                "prompt": row["prompt"],
                "created_at": row["created_at"],
                "selected_node_id": row["selected_node_id"]
            })
            # Edges
            if row["selected_node_id"]:
                add_edge(graph_id, f"device:{row['selected_node_id']}", "routed_to")

        # 14. Parallel Consensus / Multi-Model runs
        for row in conn.execute("SELECT * FROM multi_model_runs").fetchall():
            mm_id = row["multi_model_run_id"]
            graph_id = f"multi_model:{mm_id}"
            add_node(graph_id, "multi_model", f"Consensus Run", {
                "multi_model_run_id": mm_id,
                "consensus_agreement_score": row["consensus_agreement_score"],
                "status": row["status"],
                "created_at": row["created_at"],
                "latency_ms": row["latency_ms"]
            })
            # Link to inference runs by matching prompt_hash or metadata
            prompt_h = row["prompt_hash"]
            if prompt_h:
                for inf_node_id, inf_node in nodes.items():
                    if inf_node_id.startswith("inference:"):
                        if inf_node["properties"].get("prompt_hash") == prompt_h:
                            add_edge(graph_id, inf_node_id, "compares")

        # 15. CrewAI Ingested Artifacts
        for row in conn.execute("SELECT * FROM crewai_ingested_artifacts").fetchall():
            cia_id = row["id"]
            graph_id = f"crewai_artifact:{cia_id}"
            add_node(graph_id, "crewai_artifact", f"CrewAI: {row['artifact_type']}", {
                "id": cia_id,
                "source_path": row["source_path"],
                "hash": row["hash"],
                "created_at": row["created_at"],
                "ingested_at": row["ingested_at"]
            })
            # Try to link to matching Task/Run mentioned in context
            try:
                ctx = json.loads(row["run_context_json"])
                run_id = ctx.get("run_id")
                task_id = ctx.get("task_id")
                if task_id and run_id:
                    add_edge(graph_id, f"task:{run_id}:{task_id}", "associated_with")
                elif run_id:
                    add_edge(graph_id, f"run:{run_id}", "associated_with")
            except Exception:
                pass

        # 16. Manual / Explicit linkages
        explicit_links = get_evidence_graph_links()
        for link in explicit_links:
            add_edge(link["source_graph_id"], link["target_graph_id"], link["relation_type"])

        # 17. Audit and detect Missing Target Nodes (Virtual Nodes)
        virtual_nodes = {}
        for edge in edges:
            src = edge["source"]
            tgt = edge["target"]
            
            # If target node doesn't exist, create it as a virtual missing node
            if tgt not in nodes and tgt not in virtual_nodes:
                prefix = tgt.split(":")[0] if ":" in tgt else "unknown"
                label = f"Missing {prefix.capitalize()} reference"
                virtual_nodes[tgt] = {
                    "id": tgt,
                    "type": prefix,
                    "label": label,
                    "properties": {"missing": True},
                    "missing": True
                }
            
            # If source node doesn't exist, create it as a virtual missing node
            if src not in nodes and src not in virtual_nodes:
                prefix = src.split(":")[0] if ":" in src else "unknown"
                label = f"Missing {prefix.capitalize()} reference"
                virtual_nodes[src] = {
                    "id": src,
                    "type": prefix,
                    "label": label,
                    "properties": {"missing": True},
                    "missing": True
                }

        # Merge virtual nodes
        nodes.update(virtual_nodes)

    finally:
        conn.close()

    return {
        "nodes": list(nodes.values()),
        "edges": edges
    }

def trace_evidence_chain(start_id: str) -> dict:
    graph = build_evidence_graph()
    nodes_map = {n["id"]: n for n in graph["nodes"]}
    
    if start_id not in nodes_map:
        # Generate virtual missing start node
        prefix = start_id.split(":")[0] if ":" in start_id else "unknown"
        nodes_map[start_id] = {
            "id": start_id,
            "type": prefix,
            "label": f"Missing start node: {start_id}",
            "properties": {"missing": True},
            "missing": True
        }

    # Build adjacency list
    adj = {}
    for edge in graph["edges"]:
        s = edge["source"]
        t = edge["target"]
        adj.setdefault(s, []).append((t, edge))
        adj.setdefault(t, []).append((s, edge))

    # Perform BFS traversal
    visited = set([start_id])
    queue = [start_id]
    traversed_edges = []
    
    while queue:
        curr = queue.pop(0)
        for neighbor, edge in adj.get(curr, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
            # Add traversed edges to the subgraph
            if edge not in traversed_edges:
                traversed_edges.append(edge)

    # Compile subgraph
    sub_nodes = [nodes_map[nid] for nid in visited if nid in nodes_map]
    return {
        "start_node_id": start_id,
        "nodes": sub_nodes,
        "edges": traversed_edges
    }

def create_manual_link(source_id: str, target_id: str, relation_type: str) -> dict:
    link_id = f"link-{uuid.uuid4().hex[:12]}"
    persist_evidence_graph_link(link_id, source_id, target_id, relation_type)
    return {
        "link_id": link_id,
        "source_graph_id": source_id,
        "target_graph_id": target_id,
        "relation_type": relation_type,
        "created_at": now_iso()
    }
