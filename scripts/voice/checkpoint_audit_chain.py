#!/usr/bin/env python3
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
AUDIT_LOG_FILE = Path(os.getenv("HELM_AUDIT_LOG_PATH", str(ROOT / "data/runtime/voice_command_audit.jsonl")))
CHECKPOINT_FILE = Path(os.getenv("HELM_CHECKPOINT_PATH", str(ROOT / "coordination/checkpoints/voice_audit_checkpoint.json")))

def main():
    sys.path.append(str(ROOT))
    from scripts.voice.verify_voice_audit_chain import verify_chain

    # 1. Verify chain integrity under exclusive lock
    import fcntl
    lock_file = AUDIT_LOG_FILE.with_suffix(".lock")
    lock_fd = None
    try:
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        res = verify_chain(skip_lock=True)
        if res != 0:
            print("Error: Chain verification failed. Checkpoint aborted.")
            sys.exit(1)

        if not AUDIT_LOG_FILE.exists() or AUDIT_LOG_FILE.stat().st_size == 0:
            print("Error: Audit file does not exist or is empty. Checkpoint aborted.")
            sys.exit(1)

        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines:
            print("Error: No events found in audit log. Checkpoint aborted.")
            sys.exit(1)

        # 2. Extract hashes and stats
        try:
            genesis_event = json.loads(lines[0])
            genesis_event_hash = genesis_event.get("event_hash")
            
            head_event = json.loads(lines[-1])
            current_chain_head = head_event.get("event_hash")
            chain_epoch = head_event.get("chain_epoch", 2)
        except Exception as e:
            print(f"Error parsing events: {e}")
            sys.exit(1)

        # Calculate file SHA-256
        file_bytes = AUDIT_LOG_FILE.read_bytes()
        audit_file_sha256 = hashlib.sha256(file_bytes).hexdigest()

        checkpoint = {
            "chain_epoch": chain_epoch,
            "event_count": len(lines),
            "genesis_event_hash": genesis_event_hash,
            "current_chain_head": current_chain_head,
            "audit_file_sha256": audit_file_sha256,
            "checkpointed_at": datetime.now(timezone.utc).isoformat(),
            "checkpoint_location": "INDEPENDENT_EVIDENCE_STORE"
        }

        # 3. Save checkpoint
        CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_FILE.write_text(json.dumps(checkpoint, indent=2))
        print(f"Success: Wrote audit chain checkpoint to {CHECKPOINT_FILE}")
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except Exception:
                pass

if __name__ == "__main__":
    main()
