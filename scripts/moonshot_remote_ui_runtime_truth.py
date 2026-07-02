import sqlite3
import subprocess
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def get_git_sha():
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def update_ui_signals():
    git_sha = get_git_sha()
    last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    signals = [
        {
            "signal_id": "canonical_ui_url",
            "name": "Canonical Local UI URL",
            "value": "http://127.0.0.1:8765/ui-moonshot"
        },
        {
            "signal_id": "canonical_ui_name",
            "name": "Canonical UI Name",
            "value": "Moonshot UI"
        },
        {
            "signal_id": "canonical_remote_ui_url",
            "name": "Canonical Remote UI URL",
            "value": "http://100.87.18.15:8765/ui-moonshot"
        },
        {
            "signal_id": "old_local_ui_8080",
            "name": "Old Local UI Port 8080 Status",
            "value": "deprecated"
        },
        {
            "signal_id": "old_relay_ui_3012",
            "name": "Old Relay UI Port 3012 Status",
            "value": "deprecated"
        },
        {
            "signal_id": "moonshot_remote_ui_status",
            "name": "Moonshot Remote UI Status",
            "value": "active/private"
        },
        {
            "signal_id": "moonshot_remote_ui_public_exposure",
            "name": "Moonshot Remote UI Public Exposure",
            "value": "blocked"
        }
    ]
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    
    try:
        for sig in signals:
            conn.execute("""
                INSERT OR REPLACE INTO runtime_truth_signals (
                    signal_id, name, value, source, source_type, last_updated,
                    ttl_seconds, freshness, confidence, evidence_link, evidence_ref, git_sha, source_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sig["signal_id"],
                sig["name"],
                sig["value"],
                "moonshot_remote_tunnel_start.sh",
                "script",
                last_updated,
                600,
                "fresh",
                1.0,
                "docs/evidence/ui/",
                "docs/evidence/ui/",
                git_sha,
                ""
            ))
        conn.commit()
        print(f"Successfully updated {len(signals)} Moonshot UI signals in Swarm Ledger.")
    finally:
        conn.close()

if __name__ == "__main__":
    update_ui_signals()
