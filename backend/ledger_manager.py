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
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()[:12]
