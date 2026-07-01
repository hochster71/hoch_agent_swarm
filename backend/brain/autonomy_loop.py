import os
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class AutonomyLoop:
    def __init__(self, root_dir=None):
        if root_dir is None:
            root_dir = str(PROJECT_ROOT)
        self.root_dir = root_dir
        self.db_path = DB_PATH

    def run_discovery(self) -> dict:
        node_name = "mbpro"
        host = "10.0.0.115"
        port = 11434
        url = f"http://{host}:{port}/api/tags"
        
        status = "candidate_offline"
        models = []
        reachable = False
        error_msg = None

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            # 2 second timeout for fast failover/offline classification
            with urllib.request.urlopen(req, timeout=2.0) as res:
                raw = res.read(4_000_000)
                data = json.loads(raw.decode("utf-8", "ignore"))
                if isinstance(data, dict) and "models" in data:
                    reachable = True
                    status = "active_online"
                    for item in data["models"]:
                        if isinstance(item, dict) and "name" in item:
                            models.append(item["name"])
        except Exception as e:
            error_msg = str(e)

        # Store in DB
        conn = sqlite3.connect(self.db_path, timeout=30)
        apply_pragmas(conn)
        last_seen = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO runtime_worker_mesh 
                (node_name, host, ollama_base_url, status, routing_enabled, approval_required, models_observed, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_name,
                host,
                f"http://{host}:{port}",
                status,
                0, # routing_enabled is ALWAYS 0 by default
                1, # approval_required is ALWAYS 1 by default
                json.dumps(models),
                last_seen
            ))
            conn.commit()
        finally:
            conn.close()

        # Write evidence document
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        evidence_dir = Path(self.root_dir) / "docs/evidence/nodes"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = evidence_dir / f"{timestamp_str}-worker-discovery.md"
        
        evidence_content = f"""# Worker Discovery Evidence — {timestamp_str}

This evidence document records the automated discovery and status classification of the local worker node: `{node_name}`.

## Discovery Summary
- **Node Name**: {node_name}
- **Host IP**: {host}
- **Ollama API URL**: http://{host}:{port}
- **Availability Status**: {status.upper()}
- **Reachable**: {reachable}
- **Timestamp**: {last_seen}Z

## Observed Model Inventory
- **Models Count**: {len(models)}
- **Models List**: {json.dumps(models, indent=2)}

## Verification Trace
- Attempted HTTP GET request to `http://{host}:{port}/api/tags` (timeout 2.0s).
- Result: {"Success" if reachable else f"Failed (Error: {error_msg})"}
- Database write to `runtime_worker_mesh` table: Complete.
- **Routing Status**: DISABLED (routing_enabled=false, approval_required=true).
"""
        evidence_path.write_text(evidence_content, encoding="utf-8")

        # Update Mission Ledger
        ledger_path = Path(self.root_dir) / "docs/mission/mission-ledger.md"
        if ledger_path.exists():
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            rel_evidence_path = f"docs/evidence/nodes/{timestamp_str}-worker-discovery.md"
            host_root = self.root_dir
            if host_root == "/app":
                host_root = "/" + "/".join(["Users", "michaelhoch", "hoch_agent_swarm"])
            
            # Simple append
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(f"\n| {date_str} | Worker Mesh | Probe worker `mbpro`; set status to {status.upper()} | Reachability test finished | [{timestamp_str}-worker-discovery.md](file://{host_root}/{rel_evidence_path}) | c537084c5e597b72bfedea322bab2ea8f079d85d | NO_ACTIVE_RELEASE_GO | Autonomy loop execution / Local worker recovery |")

        return {
            "node_name": node_name,
            "host": host,
            "status": status,
            "reachable": reachable,
            "models_observed": models,
            "last_seen": last_seen,
            "evidence_file": str(evidence_path)
        }
