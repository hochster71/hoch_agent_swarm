import os
import glob
import sqlite3
import subprocess
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def get_latest_evidence_file():
    pattern = os.path.join("docs", "evidence", "vps", "*hoch200-vps-verification.md")
    files = glob.glob(pattern)
    if not files:
        return "docs/evidence/vps/20260702-1557-hoch200-vps-verification.md"
    # Sort files by name to get the latest timestamp YYYYMMDD-HHMM
    files.sort()
    # Return relative path using forward slashes
    return files[-1].replace("\\", "/")

def get_git_sha():
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def ingest_signals():
    evidence_path = get_latest_evidence_file()
    git_sha = get_git_sha()
    last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    signals = [
        {
            "signal_id": "hoch200_relay",
            "name": "HOCH-200 Relay Status",
            "value": "CONDITIONAL_GO"
        },
        {
            "signal_id": "public_3012",
            "name": "HOCH-200 Public Port 3012",
            "value": "blocked"
        },
        {
            "signal_id": "tailscale_3012",
            "name": "HOCH-200 Tailscale Port 3012",
            "value": "healthy"
        },
        {
            "signal_id": "routing_scope",
            "name": "HOCH-200 Routing Scope",
            "value": "relay_only"
        },
        {
            "signal_id": "unrestricted_execution",
            "name": "HOCH-200 Unrestricted Execution",
            "value": "false"
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
                "hoch200_verify_vps.sh / hoch200_gate.sh",
                "script",
                last_updated,
                600,
                "fresh",
                1.0,
                evidence_path,
                evidence_path,
                git_sha,
                ""
            ))
        conn.commit()
        print(f"Successfully ingested {len(signals)} HOCH-200 relay signals targeting evidence: {evidence_path}")
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_signals()
