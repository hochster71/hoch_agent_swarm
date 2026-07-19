#!/usr/bin/env python3
import json
import os
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_LOG_FILE = Path(os.getenv("HELM_AUDIT_LOG_PATH", str(ROOT / "data/runtime/voice_command_audit.jsonl")))

def _compute_hash(data: dict) -> str:
    # Exclude event_hash itself from the hash calculation
    temp = {k: v for k, v in data.items() if k != "event_hash"}
    serialized = json.dumps(temp, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def verify_chain(skip_lock: bool = False) -> int:
    print("=======================================================================")
    print("HELM Voice Gateway Audit Chain Verifier")
    print("=======================================================================")

    if not AUDIT_LOG_FILE.exists():
        print(f"Audit log file does not exist at {AUDIT_LOG_FILE}")
        print("Verification: SKIPPED (No events logged yet)")
        return 0

    import fcntl
    lock_file = AUDIT_LOG_FILE.with_suffix(".lock")
    lock_fd = None
    try:
        if not skip_lock:
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_SH)

        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        if not lines:
            print("Audit log file is empty.")
            print("Verification: PASS (Empty chain is valid)")
            return 0

        prev_hash = "GENESIS"
        seen_event_ids = set()
        genesis_seen = False

        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # Enforce 64 KiB size limit (measured in actual encoded bytes + terminating LF)
            stored_len = len(line.encode("utf-8")) + 1
            if stored_len > 65536:
                print(f"[-] Line {i+1} size exceeds maximum limit of 64 KiB: {stored_len} bytes")
                return 1

            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[-] Line {i+1} is not valid JSON: {e}")
                return 1

            event_id = event.get("event_id")
            if not event_id:
                print(f"[-] Event on line {i+1} is missing 'event_id'")
                return 1
                
            if event_id in seen_event_ids:
                print(f"[-] Duplicate event ID detected: {event_id} on line {i+1}")
                return 1
            seen_event_ids.add(event_id)

            # Genesis Constraints
            is_genesis = (event.get("event_type") == "AUDIT_CHAIN_RECOVERY_GENESIS")
            if i == 0:
                if not is_genesis:
                    print(f"[-] First event is not the authorized Epoch 2 recovery genesis event")
                    return 1
                genesis_seen = True
            else:
                if is_genesis:
                    print(f"[-] Duplicate genesis event detected on line {i+1}")
                    return 1
                    
            # Epoch constraint
            epoch = event.get("chain_epoch")
            if epoch is None or epoch < 2:
                print(f"[-] Invalid chain epoch {epoch} on line {i+1}")
                return 1

            # Verify event hash
            stored_hash = event.get("event_hash")
            if not stored_hash:
                print(f"[-] Event {event_id} on line {i+1} is missing 'event_hash'")
                return 1

            computed_hash = _compute_hash(event)
            if stored_hash != computed_hash:
                print(f"[-] Tampering Detected at event {event_id} (line {i+1})!")
                print(f"    Stored Hash:   {stored_hash}")
                print(f"    Computed Hash: {computed_hash}")
                return 1

            # Verify chain hash link
            stored_prev_hash = event.get("previous_event_hash")
            if stored_prev_hash != prev_hash:
                print(f"[-] Chain Broken at event {event_id} (line {i+1})!")
                print(f"    Expected Prev: {prev_hash}")
                print(f"    Stored Prev:   {stored_prev_hash}")
                return 1

            # Validate recovery genesis signature & key trust & approval artifact
            if is_genesis:
                auth = event.get("authorization")
                if not auth:
                    print(f"[-] Event {event_id} is missing 'authorization'")
                    return 1
                
                # Check signature scope
                scope = auth.get("signature_scope")
                if scope != "COMPLETE_RECOVERY_GENESIS_EVENT_V1":
                    print(f"[-] Event {event_id} has invalid signature scope: {scope}")
                    return 1

                sig_hex = auth.get("signature")
                if not sig_hex:
                    print(f"[-] Event {event_id} is missing authorization signature")
                    return 1

                # Verify approval artifact content & hash
                approval_meta = auth.get("approval_artifact")
                if not approval_meta:
                    print(f"[-] Event {event_id} is missing approval_artifact metadata")
                    return 1
                
                approval_path_str = approval_meta.get("path")
                if not approval_path_str:
                    print(f"[-] Event {event_id} approval path is missing")
                    return 1
                    
                approval_path = ROOT / approval_path_str
                if not approval_path.exists():
                    print(f"[-] Approval artifact not found at: {approval_path}")
                    return 1
                
                with open(approval_path, "rb") as app_f:
                    approval_bytes = app_f.read()
                
                # Verify hash matches
                computed_app_sha = hashlib.sha256(approval_bytes).hexdigest()
                stored_app_sha = approval_meta.get("sha256")
                if computed_app_sha != stored_app_sha:
                    print(f"[-] Approval artifact SHA-256 mismatch! Expected {stored_app_sha}, computed {computed_app_sha}")
                    return 1
                
                # Parse and verify contents
                try:
                    approval_content = json.loads(approval_bytes)
                except Exception as e:
                    print(f"[-] Malformed approval artifact JSON: {e}")
                    return 1
                    
                if approval_content.get("decision") != "APPROVED":
                    print(f"[-] Approval decision is not APPROVED")
                    return 1
                if approval_content.get("approved_by") != "michael-bryan-hoch":
                    print(f"[-] Approval decision was not approved by michael-bryan-hoch")
                    return 1

                # Verify Ed25519 signature over canonical payload
                try:
                    unsigned_event = {
                        **event,
                        "authorization": {
                            k: v
                            for k, v in auth.items()
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
                    
                    pub_key_path = ROOT / "coordination/security/voice_recovery_public_key.pem"
                    if not pub_key_path.exists():
                        print(f"[-] Recovery public key not found at {pub_key_path}")
                        return 1
                        
                    from cryptography.hazmat.primitives.asymmetric import ed25519
                    from cryptography.hazmat.primitives import serialization
                    with open(pub_key_path, "rb") as pub_f:
                        public_key = serialization.load_pem_public_key(pub_f.read())

                    # Check public key fingerprint match
                    der_bytes = public_key.public_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    computed_fp = hashlib.sha256(der_bytes).hexdigest()
                    PINNED_FINGERPRINT = "31b24ddee05364dc9648dd77cad94704c3af0b3c75b38cc40201c69d8aa725a3"
                    if computed_fp != PINNED_FINGERPRINT:
                        print(f"[-] Public key fingerprint mismatch! Expected {PINNED_FINGERPRINT}, got {computed_fp}")
                        return 1
                        
                    # Verify key manifest file
                    manifest_path = ROOT / "coordination/security/voice_recovery_key_manifest.json"
                    if not manifest_path.exists():
                        print(f"[-] Key manifest not found at {manifest_path}")
                        return 1
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as mf:
                            manifest = json.load(mf)
                        if manifest.get("key_id") != "HELM-FOUNDER-RECOVERY-KEY-001":
                            print(f"[-] Invalid key ID in manifest: {manifest.get('key_id')}")
                            return 1
                        if manifest.get("public_key_der_sha256") != computed_fp:
                            print("[-] Pinned public key in manifest does not match actual public key fingerprint")
                            return 1
                        if manifest.get("status") != "ACTIVE":
                            print(f"[-] Key manifest status is not ACTIVE: {manifest.get('status')}")
                            return 1
                        if manifest.get("owner") != "michael-bryan-hoch":
                            print(f"[-] Key manifest owner is not michael-bryan-hoch")
                            return 1
                    except Exception as e:
                        print(f"[-] Error validating key manifest: {e}")
                        return 1

                    # Verify key trust attestation file
                    attestation_path = ROOT / "coordination/security/founder_key_trust_attestation.json"
                    if not attestation_path.exists():
                        print(f"[-] Key trust attestation not found at {attestation_path}")
                        return 1
                    try:
                        with open(attestation_path, "r", encoding="utf-8") as af:
                            attestation = json.load(af)
                        if attestation.get("decision") != "APPROVED":
                            print(f"[-] Trust attestation decision is not APPROVED")
                            return 1
                        if attestation.get("actor_id") != "michael-bryan-hoch":
                            print(f"[-] Trust attestation actor is not michael-bryan-hoch")
                            return 1
                        if attestation.get("trusted_public_key_der_sha256") != computed_fp:
                            print("[-] Pinned public key in trust attestation does not match actual public key fingerprint")
                            return 1
                        if attestation.get("status") != "ACTIVE":
                            print(f"[-] Trust attestation status is not ACTIVE")
                            return 1
                        
                        # Contradiction checks
                        if attestation.get("decision_maker") != attestation.get("actor_id"):
                            print("[-] Trust attestation contradiction: decision_maker does not match actor_id")
                            return 1
                        if attestation.get("fingerprint_displayed_to_decision_maker") != attestation.get("trusted_public_key_der_sha256"):
                            print("[-] Trust attestation contradiction: fingerprint_displayed_to_decision_maker does not match trusted_public_key_der_sha256")
                            return 1
                        if attestation.get("fingerprint_approved") is not True:
                            print("[-] Trust attestation: fingerprint_approved is not true")
                            return 1
                        if attestation.get("decision_capture_method") != "EXPLICIT_FOUNDER_APPROVAL":
                            print("[-] Trust attestation: decision_capture_method is not EXPLICIT_FOUNDER_APPROVAL")
                            return 1
                    except Exception as e:
                        print(f"[-] Error validating key trust attestation: {e}")
                        return 1

                    public_key.verify(bytes.fromhex(sig_hex), canonical_payload)
                    print(f"[+] Recovery genesis event signature verified successfully via Ed25519 public key")
                except Exception as e:
                    print(f"[-] Recovery genesis event signature verification failed: {e}")
                    return 1

            prev_hash = stored_hash
            print(f"[+] Verified event {event_id} (hash link: {prev_hash[:12]}...)")

        # Verify checkpoint alignment (if the checkpoint file exists and not running in tests)
        checkpoint_path = Path(os.getenv("HELM_CHECKPOINT_PATH", str(ROOT / "coordination/checkpoints/voice_audit_checkpoint.json")))
        if checkpoint_path.exists() and "pytest" not in sys.modules:
            try:
                with open(checkpoint_path, "r", encoding="utf-8") as cf:
                    checkpoint = json.load(cf)
                
                # Check event count matches lines (non-empty lines)
                non_empty_lines = [l for l in lines if l.strip()]
                if checkpoint.get("event_count") != len(non_empty_lines):
                    print(f"[-] Checkpoint verification failed: event_count mismatch. Expected {checkpoint.get('event_count')}, got {len(non_empty_lines)}")
                    return 1
                
                # Check genesis event hash matches
                first_evt = json.loads(non_empty_lines[0])
                if checkpoint.get("genesis_event_hash") != first_evt.get("event_hash"):
                    print("[-] Checkpoint verification failed: genesis_event_hash mismatch")
                    return 1
                
                # Check current chain head matches last event's hash
                last_evt = json.loads(non_empty_lines[-1])
                if checkpoint.get("current_chain_head") != last_evt.get("event_hash"):
                    print("[-] Checkpoint verification failed: current_chain_head mismatch")
                    return 1
                
                # Check audit file SHA-256 matches
                file_bytes = AUDIT_LOG_FILE.read_bytes()
                computed_file_sha = hashlib.sha256(file_bytes).hexdigest()
                if checkpoint.get("audit_file_sha256") != computed_file_sha:
                    print("[-] Checkpoint verification failed: audit_file_sha256 mismatch")
                    return 1
                
                print("[+] Verified log file alignment with external checkpoint record")
            except Exception as e:
                print(f"[-] Error verifying checkpoint alignment: {e}")
                return 1

        print("=======================================================================")
        print("\033[92mAUDIT EVENT HASH CHAIN VERIFIED SUCCESSFULLY [PASS]\033[0m")
        return 0

    except Exception as e:
        print(f"Error executing chain verification: {e}")
        return 1
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except Exception:
                pass

if __name__ == "__main__":
    sys.exit(verify_chain())
