import os
import sqlite3
import hashlib
import json
import threading
from datetime import datetime
from backend.db.sqlite_pragmas import apply_wal_pragmas

DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "swarm_ledger.db"))
_db_lock = threading.Lock()

def init_db():
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ledger_blocks (
                    idx INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    event TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
            """)
            conn.commit()
            
            # Check if empty, and write genesis block if so
            cursor.execute("SELECT COUNT(*) FROM ledger_blocks")
            count = cursor.fetchone()[0]
            if count == 0:
                # Create Genesis Block
                genesis_event = {
                    "actor": {
                        "id": "system",
                        "name": "System Genesis",
                        "type": "system",
                        "role": "System"
                    },
                    "action": {
                        "type": "GENESIS_INITIALIZED",
                        "summary": "Swarm control immutable ledger initialized."
                    },
                    "target": {
                        "type": "system",
                        "id": "ledger",
                        "name": "Immutable Ledger"
                    },
                    "result": "success",
                    "severity": "info",
                    "provenance": {
                        "source": "system",
                        "evidence_refs": []
                    },
                    "policy": {
                        "required": False,
                        "result": "not_required"
                    }
                }
                
                genesis_ts = "2026-06-24T00:00:00Z"
                genesis_event_id = "evt-genesis-000"
                genesis_event_str = json.dumps(genesis_event, separators=(',', ':'), sort_keys=True)
                genesis_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
                
                # calculate hash
                raw_str = f"0|{genesis_ts}|{genesis_event_id}|{genesis_event_str}|{genesis_prev_hash}"
                genesis_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
                
                cursor.execute(
                    "INSERT INTO ledger_blocks (idx, timestamp, event_id, event, previous_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
                    (0, genesis_ts, genesis_event_id, genesis_event_str, genesis_prev_hash, genesis_hash)
                )
                conn.commit()
        finally:
            conn.close()

def get_latest_block():
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idx, timestamp, event_id, event, previous_hash, hash FROM ledger_blocks ORDER BY idx DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "index": row[0],
                    "timestamp": row[1],
                    "event_id": row[2],
                    "event": json.loads(row[3]),
                    "previous_hash": row[4],
                    "hash": row[5]
                }
            return None
        finally:
            conn.close()

def add_event_to_ledger(event: dict) -> dict:
    # Ensure event has id
    event_id = event.get("id", f"evt-{uuid_like_hash(event)}")
    
    init_db()
    latest = get_latest_block()
    
    next_idx = 1
    prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    if latest:
        next_idx = latest["index"] + 1
        prev_hash = latest["hash"]
        
    ts = event.get("timestamp", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
    
    # Consistent JSON serialization
    event_str = json.dumps(event, separators=(',', ':'), sort_keys=True)
    
    raw_str = f"{next_idx}|{ts}|{event_id}|{event_str}|{prev_hash}"
    block_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ledger_blocks (idx, timestamp, event_id, event, previous_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
                (next_idx, ts, event_id, event_str, prev_hash, block_hash)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Event already in ledger (avoid duplicates)
            pass
        finally:
            conn.close()
        
    return {
        "index": next_idx,
        "timestamp": ts,
        "event_id": event_id,
        "event": event,
        "previous_hash": prev_hash,
        "hash": block_hash
    }

def get_ledger_blocks() -> list:
    init_db()
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT idx, timestamp, event_id, event, previous_hash, hash FROM ledger_blocks ORDER BY idx ASC")
            rows = cursor.fetchall()
        finally:
            conn.close()
        
    blocks = []
    for r in rows:
        blocks.append({
            "index": r[0],
            "timestamp": r[1],
            "event_id": r[2],
            "event": json.loads(r[3]),
            "previous_hash": r[4],
            "hash": r[5]
        })
    return blocks

def verify_ledger_chain() -> dict:
    blocks = get_ledger_blocks()
    corrupted_indices = []
    
    if not blocks:
        return {
            "is_valid": True,
            "block_count": 0,
            "corrupted_block_indices": [],
            "verification_msg": "Ledger is empty. Integrity verified.",
            "verified_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
    expected_prev_hash = blocks[0]["previous_hash"]
    
    for block in blocks:
        # Check previous hash continuity
        if block["previous_hash"] != expected_prev_hash:
            corrupted_indices.append(block["index"])
            expected_prev_hash = block["hash"]
            continue
            
        # Recalculate hash
        event_str = json.dumps(block["event"], separators=(',', ':'), sort_keys=True)
        raw_str = f"{block['index']}|{block['timestamp']}|{block['event_id']}|{event_str}|{block['previous_hash']}"
        calculated_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
        
        if block["hash"] != calculated_hash:
            corrupted_indices.append(block["index"])
            
        expected_prev_hash = block["hash"]
        
    is_valid = len(corrupted_indices) == 0
    msg = f"Cryptographic chain intact. Verified {len(blocks)} blocks." if is_valid else f"Ledger corruption detected! Failed blocks: {corrupted_indices}"
    
    return {
        "is_valid": is_valid,
        "block_count": len(blocks),
        "corrupted_block_indices": corrupted_indices,
        "verification_msg": msg,
        "verified_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

def uuid_like_hash(data: dict) -> str:
    serialized = json.dumps(data, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]

def log_operator_action(
    action_name: str,
    endpoint: str,
    preflight: dict,
    decision: str,
    override_reason: str = "",
    execution_output: dict = None,
    artifact_refs: list = None,
    recovery_command: str = ""
) -> dict:
    import subprocess
    from backend.runtime_paths import optional_ag_scratch_root
    COCKPIT_DIR = optional_ag_scratch_root()
    
    # Get Git SHA & dirty state
    git_sha = "unknown"
    git_dirty = False
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=COCKPIT_DIR, capture_output=True, text=True, timeout=1.0)
        if res.returncode == 0:
            git_sha = res.stdout.strip()
        res_status = subprocess.run(["git", "status", "--porcelain"], cwd=COCKPIT_DIR, capture_output=True, text=True, timeout=1.0)
        git_dirty = bool(res_status.stdout.strip())
    except Exception:
        pass
        
    git_state = {
        "commit_sha": git_sha,
        "dirty": git_dirty
    }

    event = {
        "id": f"evt-{uuid_like_hash({'timestamp': datetime.utcnow().isoformat(), 'action': action_name})}",
        "actor": {
            "id": "operator",
            "name": "System Operator",
            "type": "operator",
            "role": "System Operator"
        },
        "action": {
            "type": "OPERATOR_ACTION",
            "name": action_name,
            "endpoint": endpoint,
            "summary": f"Executed high-impact action: {action_name}"
        },
        "preflight": preflight,
        "decision": decision,
        "override_reason": override_reason,
        "execution_context": {
            "git_state": git_state,
            "execution_output": execution_output or {},
            "recovery_command": recovery_command,
            "artifact_refs": artifact_refs or []
        },
        "result": "success",
        "severity": "info",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    return add_event_to_ledger(event)

def generate_evidence_pack(block_idx: int) -> dict:
    from pathlib import Path
    init_db()
    # Find block
    block = None
    blocks = get_ledger_blocks()
    for b in blocks:
        if b["index"] == block_idx:
            block = b
            break
            
    if not block:
        raise ValueError(f"Block at index {block_idx} not found in immutable ledger.")
        
    # Run chain verification
    verification = verify_ledger_chain()
    
    # Process artifact references
    artifact_refs = block["event"].get("execution_context", {}).get("artifact_refs", [])
    artifacts_content = []
    
    for ref in artifact_refs:
        ref_path = Path(ref)
        if ref_path.exists() and ref_path.is_file():
            try:
                content_bytes = ref_path.read_bytes()
                sha256 = hashlib.sha256(content_bytes).hexdigest()
                
                is_text = False
                text_content = ""
                if ref_path.suffix in [".json", ".jsonl", ".txt", ".md", ".yaml", ".yml", ".spdx"] and len(content_bytes) < 1024 * 1024:
                    try:
                        text_content = content_bytes.decode("utf-8")
                        is_text = True
                    except Exception:
                        pass
                
                artifacts_content.append({
                    "path": str(ref_path),
                    "size_bytes": len(content_bytes),
                    "sha256": sha256,
                    "is_text": is_text,
                    "content": text_content if is_text else "[Binary / Large Content]"
                })
            except Exception as e:
                artifacts_content.append({
                    "path": str(ref_path),
                    "error": f"Failed to read file: {e}"
                })
        else:
            artifacts_content.append({
                "path": str(ref_path),
                "error": "File does not exist or is not a file"
            })
            
    return {
        "ledger_block": block,
        "chain_verification": verification,
        "artifacts_content": artifacts_content,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

def create_audit_review_bundle() -> bytes:
    import io
    import zipfile
    
    blocks = get_ledger_blocks()
    verification = verify_ledger_chain()
    
    from backend.preflight_gate import GATE
    preflight = GATE.run_preflight()
    
    from backend.model_health_monitor import MONITOR
    model_health = MONITOR.scan_health(force=False)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        blocks_data = json.dumps(blocks, indent=2)
        zip_file.writestr("ledger_blocks.json", blocks_data)
        
        verify_data = json.dumps(verification, indent=2)
        zip_file.writestr("chain_verification.json", verify_data)
        
        preflight_data = json.dumps(preflight, indent=2)
        zip_file.writestr("preflight_status.json", preflight_data)
        
        health_data = json.dumps(model_health, indent=2)
        zip_file.writestr("model_health.json", health_data)
        
        manifest_lines = []
        for name in ["ledger_blocks.json", "chain_verification.json", "preflight_status.json", "model_health.json"]:
            content = zip_file.read(name)
            h = hashlib.sha256(content).hexdigest()
            manifest_lines.append(f"{h}  {name}\n")
            
        zip_file.writestr("manifest.sha256", "".join(manifest_lines))
        
    return zip_buffer.getvalue()

def get_handoff_status() -> dict:
    import subprocess
    from pathlib import Path
    
    branch = ""
    commit_sha = ""
    is_dirty = True
    
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        status_out = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        is_dirty = len(status_out) > 0
    except Exception:
        pass
        
    active_tag = "0.1.6-ERROR-BUDGET-AWARE-AUTONOMY"
    
    from backend.preflight_gate import GATE
    preflight = GATE.run_preflight()
    preflight_score = preflight.get("overall_score", 0)
    preflight_pass = preflight.get("go_no_go") == "GO"
    
    from backend.ledger_manager import verify_ledger_chain
    ledger_verify = verify_ledger_chain()
    ledger_pass = ledger_verify.get("is_valid", False)
    
    from backend.model_health_monitor import MONITOR
    model_health = MONITOR.scan_health(force=False)
    providers = model_health.get("providers", {})
    health_pass = any(p.get("status") == "online" for p in providers.values()) if providers else False
    
    manifest = [
        {"file": "swarm_ledger.db", "desc": "SQLite immutable action ledger database", "status": "READY"},
        {"file": "ledger_blocks.json", "desc": "JSON export of ledger transactions list", "status": "READY"},
        {"file": "preflight_status.json", "desc": "Latest preflight checklist status report", "status": "READY"},
        {"file": "model_health.json", "desc": "Model health diagnostics and probe metrics", "status": "READY"},
        {"file": "run_report.json", "desc": "Latest Crew campaign run metrics", "status": "READY" if Path("run_report.json").exists() else "NOT_FOUND"},
        {"file": "manifest.sha256", "desc": "Cryptographic checksum index file", "status": "READY"}
    ]
    
    return {
        "git": {
            "branch": branch,
            "commit_sha": commit_sha,
            "dirty": is_dirty,
            "active_tag": active_tag
        },
        "gates": {
            "preflight_score": preflight_score,
            "preflight_pass": preflight_pass,
            "ledger_pass": ledger_pass,
            "model_health_pass": health_pass,
            "compliance_pass": preflight_pass and ledger_pass and health_pass
        },
        "manifest": manifest
    }

def create_handoff_packet() -> bytes:
    import io
    import zipfile
    import json
    import os
    import hashlib
    from pathlib import Path
    
    status = get_handoff_status()
    
    from backend.ledger_manager import get_ledger_blocks, DB_FILE
    blocks = get_ledger_blocks()
    
    from backend.preflight_gate import GATE
    preflight = GATE.run_preflight()
    
    from backend.model_health_monitor import MONITOR
    model_health = MONITOR.scan_health(force=False)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("ledger_blocks.json", json.dumps(blocks, indent=2))
        zip_file.writestr("preflight_status.json", json.dumps(preflight, indent=2))
        zip_file.writestr("model_health.json", json.dumps(model_health, indent=2))
        zip_file.writestr("handoff_status.json", json.dumps(status, indent=2))
        
        if os.path.exists(DB_FILE):
            zip_file.write(DB_FILE, "swarm_ledger.db")
            
        if os.path.exists("run_report.json"):
            zip_file.write("run_report.json", "run_report.json")
            
        manifest_lines = []
        for name in zip_file.namelist():
            content = zip_file.read(name)
            h = hashlib.sha256(content).hexdigest()
            manifest_lines.append(f"{h}  {name}\n")
            
        zip_file.writestr("manifest.sha256", "".join(manifest_lines))
        
    return zip_buffer.getvalue()
