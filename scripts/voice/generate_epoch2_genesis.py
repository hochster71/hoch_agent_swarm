import os
import json
import hashlib
import argparse
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[2]
PRIV_KEY_PATH = Path(os.path.expanduser("~/Library/Application Support/HELM/keys/voice_recovery_private_key.pem"))
AUDIT_LOG_FILE = Path(os.getenv("HELM_AUDIT_LOG_PATH", str(ROOT / "data/runtime/voice_command_audit.jsonl")))
APPROVAL_FILE = ROOT / "coordination/approvals/voice_epoch2_recovery_approval.json"

def main():
    parser = argparse.ArgumentParser(description="Generate Epoch 2 Recovery Genesis Event")
    parser.add_argument("--force-recovery-override", action="store_true", help="Force override of existing genesis candidate")
    args = parser.parse_args()

    import fcntl
    lock_file = AUDIT_LOG_FILE.with_suffix(".lock")
    lock_fd = None
    try:
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # 1. Guard against overwriting operational logs or unexpected contents
        if AUDIT_LOG_FILE.exists() and AUDIT_LOG_FILE.stat().st_size > 0:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            
            if len(lines) == 0:
                pass
            elif len(lines) == 1:
                # Check if it's exactly the initialization candidate
                try:
                    evt = json.loads(lines[0])
                    if evt.get("event_type") == "AUDIT_CHAIN_RECOVERY_GENESIS" and evt.get("chain_epoch") == 2:
                        if not args.force_recovery_override:
                            print("Guard Triggered: File contains exactly an initialization candidate. Override requires --force-recovery-override.")
                            return
                    else:
                        print("Guard Triggered: File contains unexpected content. Initialization aborted (fail closed).")
                        return
                except Exception:
                    print("Guard Triggered: File contains malformed content. Initialization aborted (fail closed).")
                    return
            else:
                # len(lines) > 1, meaning operational events or extra lines exist
                print("Guard Triggered: Operational events detected. Replacement prohibited.")
                return

        # 2. Verify approval file and get its SHA-256
        if not APPROVAL_FILE.exists():
            print(f"Error: Approval file {APPROVAL_FILE} does not exist.")
            return
        with open(APPROVAL_FILE, "rb") as f:
            approval_bytes = f.read()
        approval_sha256 = hashlib.sha256(approval_bytes).hexdigest()

        # 3. Load private key
        if not PRIV_KEY_PATH.exists():
            print(f"Error: Private key {PRIV_KEY_PATH} not found.")
            return
        with open(PRIV_KEY_PATH, "rb") as f:
            priv_key = serialization.load_pem_private_key(f.read(), password=None)

        # 4. Construct recovery genesis event
        event = {
            "event_type": "AUDIT_CHAIN_RECOVERY_GENESIS",
            "chain_epoch": 2,
            "previous_event_hash": "GENESIS",
            "prior_file_last_known_hash": None,
            "prior_file_last_known_hash_state": "NOT_PROVEN",
            "prior_file_sha256": "5ebebdaa035c1cb7709b4f9c6008f6944f740850d552e51e2e2b64f380f43fe5",
            "reconstructed_file_sha256": "118166172254cff15e549c2af94034ebc6dfe5184fe9e78a4504e62fff42e485",
            "recovery_reason": "LEGACY_CHAIN_FORMAT_AND_EOF_READER_DEFECT",
            "historical_originality_preserved": False,
            "eligible_for_live_control": False,
            "event_id": "VOICE-EVT-RECOVERY-GENESIS",
            "authorization": {
                "actor_id": "michael-bryan-hoch",
                "authority": "FOUNDER",
                "decision": "APPROVED",
                "approved_at": "2026-07-19T16:32:00Z",
                "approval_artifact": {
                    "path": "coordination/approvals/voice_epoch2_recovery_approval.json",
                    "sha256": approval_sha256,
                    "content_verified": True
                },
                "signature_algorithm": "Ed25519",
                "signature_scope": "COMPLETE_RECOVERY_GENESIS_EVENT_V1"
            }
        }

        # 5. Sign the complete canonical payload excluding 'event_hash' and 'signature'
        unsigned_event = {
            **event,
            "authorization": {
                k: v
                for k, v in event["authorization"].items()
                if k != "signature"
            }
        }
        unsigned_event.pop("event_hash", None)
        canonical_payload = json.dumps(
            unsigned_event,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")

        signature = priv_key.sign(canonical_payload)
        event["authorization"]["signature"] = signature.hex()

        # 6. Compute final event_hash
        temp = {k: v for k, v in event.items() if k != "event_hash"}
        serialized = json.dumps(temp, sort_keys=True)
        event["event_hash"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        # 7. Write to audit file
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        serialized_line = json.dumps(event) + "\n"
        encoded_line = serialized_line.encode("utf-8")
        if len(encoded_line) > 65536:
             raise ValueError(f"Genesis event exceeds 64 KiB limit: {len(encoded_line)} bytes")

        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(serialized_line)

        print("Success: Generated and signed Epoch 2 genesis event in the live audit log.")
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except Exception:
                pass

if __name__ == "__main__":
    main()
