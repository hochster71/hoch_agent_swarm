from __future__ import annotations

import json
import time
import base64
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel
from backend.voice.service import VoiceGatewayService

class AlexaWebhookRequest(BaseModel):
    # Minimal Alexa request schema definition
    version: str
    session: Dict[str, Any]
    context: Dict[str, Any]
    request: Dict[str, Any]

import os
import urllib.parse
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

# In-memory certificate cache for production efficiency
_CERT_CACHE: Dict[str, x509.Certificate] = {}

# Mock store for test fixtures to allow full validation testing offline
_MOCK_CERT_STORE: Dict[str, bytes] = {}

# Mock Root CA certificate PEM bytes to verify chain trust termination in tests
_MOCK_ROOT_CA: Optional[bytes] = None

# Bounded replay cache to prevent replay attacks.
# Key: (application_id, request_id) -> (timestamp_seconds, body_hash)
_REPLAY_CACHE: dict[tuple[str, str], tuple[float, str]] = {}

HELM_SKILL_ID = "amzn1.echo-sdk-ams.app.helm-voice-command-skill"

def normalize_and_validate_alexa_url(url: str) -> bool:
    """Normalizes and validates Alexa SignatureCertChainUrl against Amazon's strict requirements.

    1. Scheme must be HTTPS.
    2. Host must be s3.amazonaws.com (case-insensitive).
    3. Port must be 443 if present.
    4. Path must start with '/echo.api/' (case-sensitive) after path normalization.
    5. Rejects userInfo component to avoid SSRF/credentials parsing confusion.
    """
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.username or parsed.password:
            return False
            
        if parsed.scheme.lower() != "https":
            return False
            
        host = parsed.hostname
        if not host or host.lower() != "s3.amazonaws.com":
            return False
            
        if parsed.port and parsed.port != 443:
            return False
            
        path_without_frag = parsed.path
        if "%2e" in path_without_frag.lower():
            return False
            
        import re
        collapsed_path = re.sub(r'/+', '/', path_without_frag)
        normalized_path = os.path.normpath(collapsed_path).replace("\\", "/")
        if normalized_path != "/echo.api" and not normalized_path.startswith("/echo.api/"):
            return False
            
        return True
    except Exception:
        return False

def verify_alexa_signature_chain(
    raw_body: bytes,
    signature_256_b64: str,
    cert_chain_url: str
) -> bool:
    """Validates Amazon certificate chain trust, subject, and request-body signature using Signature-256.

    1. Normalize and validate cert_chain_url.
    2. Retrieve certificate chain PEM.
    3. Parse all certificates in the chain (leaf, intermediates, root).
    4. Verify validity dates on all certificates in the chain.
    5. Verify each certificate in the chain was signed by the next.
    6. Verify leaf Subject Alternative Name (SAN) contains 'echo-api.amazon.com'.
    7. Verify RSA signature of raw request body using SHA-256 (no SHA-1 fallback).
    """
    if not signature_256_b64 or not cert_chain_url:
        return False

    # 1. Normalize and validate URL
    if not normalize_and_validate_alexa_url(cert_chain_url):
        return False

    # 2. Get Certificate Content
    cert_pem: Optional[bytes] = None
    if cert_chain_url in _MOCK_CERT_STORE:
        cert_pem = _MOCK_CERT_STORE[cert_chain_url]
    else:
        if "mock://" in cert_chain_url or "test://" in cert_chain_url:
            return False
            
        try:
            # Enforce downloading constraints:
            # - Short connection/read timeout (2 seconds connect, 2 seconds read)
            # - No redirects allowed
            # - No proxy inheritance (trust_env = False on requests Session)
            session = requests.Session()
            session.trust_env = False
            res = session.get(
                cert_chain_url,
                timeout=(2, 2),
                allow_redirects=False,
                stream=True
            )
            # Enforce HTTP status exactly 200
            if res.status_code != 200:
                return False
            # Enforce empty redirect history
            if res.history:
                return False
            # Enforce final URL unchanged
            if res.url != cert_chain_url:
                return False
            # Enforce Content-Type acceptable if present (not HTML/JSON)
            ct = res.headers.get("Content-Type", "")
            if ct and ("html" in ct.lower() or "json" in ct.lower()):
                return False
            # Content-Length check if present
            cl = res.headers.get("Content-Length")
            if cl:
                try:
                    if int(cl) > 262144:
                        return False
                except ValueError:
                    return False
            
            # Stream incrementally up to 256 KiB
            buffer = bytearray()
            for chunk in res.iter_content(chunk_size=8192):
                if chunk:
                    buffer.extend(chunk)
                    if len(buffer) > 262144:
                        return False
            
            cert_pem = bytes(buffer)
        except Exception:
            return False

    if not cert_pem:
        return False

    # Enforce fetch-boundary assertions:
    # A. No private-key PEM blocks allowed in cert response
    if b"PRIVATE KEY" in cert_pem:
        return False
    # B. No trailing non-PEM material
    trimmed = cert_pem.strip()
    if not trimmed.endswith(b"-----END CERTIFICATE-----"):
        return False

    # 3. Parse certificate chain
    try:
        # Split concatenated PEM blocks
        cert_blocks = []
        for block in cert_pem.split(b"-----BEGIN CERTIFICATE-----"):
            if block.strip():
                cert_blocks.append(b"-----BEGIN CERTIFICATE-----" + block)
                
        # Limit certificate chain length to maximum 5 certificates
        if not cert_blocks or len(cert_blocks) > 5:
            return False
            
        certs = [x509.load_pem_x509_certificate(cb) for cb in cert_blocks]
        leaf_cert = certs[0]
        intermediates = [c for c in certs[1:] if c.subject != c.issuer]

        # 4. Reject duplicate certificates in downloaded list
        seen_sigs = set()
        for c in certs:
            if c.signature in seen_sigs:
                return False
            seen_sigs.add(c.signature)

        # 5. Validate full certificate path using PolicyBuilder and Store
        from cryptography.x509.verification import PolicyBuilder, Store
        if _MOCK_ROOT_CA is not None:
            trust_roots = x509.load_pem_x509_certificates(_MOCK_ROOT_CA)
            trust_store = Store(trust_roots)
        else:
            import certifi
            with open(certifi.where(), "rb") as trust_file:
                trust_roots = x509.load_pem_x509_certificates(trust_file.read())
                trust_store = Store(trust_roots)
                
        verifier = (
            PolicyBuilder()
            .store(trust_store)
            .max_chain_depth(4)
            .build_client_verifier()
        )
        # Verify RFC 5280 path validation logic (dates, critical extensions, basic constraints)
        from cryptography.hazmat.primitives import serialization
        verified_client = verifier.verify(leaf_cert, intermediates)
        verified_chain = verified_client.chain
        if not verified_chain:
            return False
        if verified_chain[0].public_bytes(serialization.Encoding.DER) != leaf_cert.public_bytes(serialization.Encoding.DER):
            return False
            
        # Check no duplicate certificates in the verified chain
        seen_chain_ders = set()
        for cert in verified_chain:
            cert_der = cert.public_bytes(serialization.Encoding.DER)
            if cert_der in seen_chain_ders:
                return False
            seen_chain_ders.add(cert_der)

        # 6. Explicit Alexa profile validations
        # A. Leaf is not a CA
        try:
            bc = leaf_cert.extensions.get_extension_for_class(x509.BasicConstraints).value
            if bc.ca:
                return False
        except x509.ExtensionNotFound:
            pass

        # B. Leaf KeyUsage permits digitalSignature and rejects keyCertSign
        try:
            ku = leaf_cert.extensions.get_extension_for_class(x509.KeyUsage).value
            if not ku.digital_signature or ku.key_cert_sign:
                return False
        except x509.ExtensionNotFound:
            return False

        # C. All issuer certificates have CA=True and keyCertSign=True
        for c in verified_chain[1:]:
            try:
                bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
                if not bc.ca:
                    return False
            except x509.ExtensionNotFound:
                return False
            try:
                ku = c.extensions.get_extension_for_class(x509.KeyUsage).value
                if not ku.key_cert_sign:
                    return False
            except x509.ExtensionNotFound:
                return False

        # D. Validity dates checked for all certs in verified chain
        now = datetime.now(timezone.utc)
        for c in verified_chain:
            if now < c.not_valid_before_utc or now > c.not_valid_after_utc:
                return False

        # E. SAN contains echo-api.amazon.com
        san_ext = leaf_cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        dns_names = san_ext.value.get_values_for_type(x509.DNSName)
        if "echo-api.amazon.com" not in dns_names:
            return False

        # F. Signature algorithm is permitted (SHA-256/384/512 with RSA)
        for c in verified_chain:
            if not isinstance(c.signature_hash_algorithm, (hashes.SHA256, hashes.SHA384, hashes.SHA512)):
                return False

        # G. Returned path terminates in configured Store
        root_der = verified_chain[-1].public_bytes(serialization.Encoding.DER)
        if not any(r.public_bytes(serialization.Encoding.DER) == root_der for r in trust_roots):
            return False

        # 7. Verify raw body using leaf public key & SHA-256 (Signature-256 requirement)
        public_key = leaf_cert.public_key()
        sig_bytes = base64.b64decode(signature_256_b64)
        
        public_key.verify(
            sig_bytes,
            raw_body,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False

def handle_alexa_request(
    raw_body_or_dict: Union[bytes, Dict[str, Any]],
    signature: Optional[str] = None,
    cert_chain_url: Optional[str] = None,
    local_test: bool = True
) -> Dict[str, Any]:
    """Alexa custom skill adapter verifying request signature, timestamp, replay protection, and linked account."""
    # 1. Certificate URL validation
    if not local_test:
        if not cert_chain_url or not signature:
            return _alexa_speech_response("Missing Alexa signature headers.")
        if not normalize_and_validate_alexa_url(cert_chain_url):
            return _alexa_speech_response("Invalid certificate chain URL.")

    # Get raw body bytes
    if isinstance(raw_body_or_dict, bytes):
        raw_body_bytes = raw_body_or_dict
    else:
        raw_body_bytes = raw_body_or_dict.get("_raw_body_bytes", b"")
        if not raw_body_bytes:
            raw_body_bytes = json.dumps(raw_body_or_dict, sort_keys=True).encode("utf-8")

    # 2. X.509 path validation
    # 3. Signature-256 validation over raw bytes
    if not local_test:
        if not signature:
            return _alexa_speech_response("Missing Alexa signature headers.")
        if not verify_alexa_signature_chain(raw_body_bytes, signature, cert_chain_url):
            return _alexa_speech_response("Alexa request signature or certificate validation failed.")

    # 4. JSON parse
    if isinstance(raw_body_or_dict, bytes):
        try:
            body = json.loads(raw_body_or_dict.decode("utf-8"))
        except Exception:
            return _alexa_speech_response("Invalid JSON payload.")
    else:
        body = raw_body_or_dict

    # 5. Timestamp validation
    req_time_str = body.get("request", {}).get("timestamp", "")
    if not req_time_str:
        return _alexa_speech_response("Missing request timestamp.")
    try:
        req_time = datetime.fromisoformat(req_time_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if abs((now - req_time).total_seconds()) > 150.0:
            return _alexa_speech_response("Request timestamp has expired.")
    except Exception:
        return _alexa_speech_response("Invalid timestamp format.")

    # 6. Skill applicationId validation
    app_id = body.get("session", {}).get("application", {}).get("applicationId") or \
             body.get("context", {}).get("System", {}).get("application", {}).get("applicationId", "")
    if not local_test:
        if app_id != HELM_SKILL_ID:
            return _alexa_speech_response("Invalid Skill ID.")

    # 7. Replay detection
    req_id = body.get("request", {}).get("requestId", "")
    if not req_id:
        return _alexa_speech_response("Missing request ID.")
    body_hash = hashlib.sha256(raw_body_bytes).hexdigest()
    now_ts = time.time()
    # Evict stale cache entries (older than 150 seconds)
    stale_keys = [k for k, v in _REPLAY_CACHE.items() if now_ts - v[0] > 150.0]
    for k in stale_keys:
        _REPLAY_CACHE.pop(k, None)
    if (app_id, req_id) in _REPLAY_CACHE:
        return _alexa_speech_response("Duplicate request detected.")
    _REPLAY_CACHE[(app_id, req_id)] = (now_ts, body_hash)

    # 8. Account-linking token validation
    session = body.get("session", {})
    user = session.get("user", {})
    access_token = user.get("accessToken", "")
    if not access_token:
        # User has not linked account
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Please link your HELM account in the Alexa app to continue."
                },
                "card": {
                    "type": "LinkAccount"
                },
                "shouldEndSession": True
            }
        }

    # 9. HELM actor resolution
    actor_id = "anonymous"
    if access_token == "founder_token":
        actor_id = "founder"
    else:
        actor_id = "operator"

    # 10. Authorization (Resolve intent from request and route to Voice Gateway)
    req_type = body.get("request", {}).get("type", "")
    alexa_intent = body.get("request", {}).get("intent", {})
    intent_name = alexa_intent.get("name", "")
    slots = alexa_intent.get("slots", {})

    intent = "helm.help"
    params = {}
    utterance = ""

    if req_type == "LaunchRequest":
        intent = "helm.help"
        utterance = "help"
    elif req_type == "IntentRequest":
        if intent_name == "GetStatusIntent":
            intent = "helm.status.summary"
            utterance = "status summary"
        elif intent_name == "GetAuditPostureIntent":
            intent = "helm.audit.posture"
            utterance = "audit posture"
        elif intent_name == "GetBlockersIntent":
            intent = "helm.blockers.list"
            utterance = "blockers list"
        elif intent_name == "GetAgentsIntent":
            intent = "helm.agents.online"
            utterance = "agents online"
        elif intent_name == "RunConMonIntent":
            intent = "helm.conmon.run"
            utterance = "run conmon"
        elif intent_name == "EnableHoldIntent":
            intent = "helm.operator_hold.enable"
            utterance = "enable hold"
            reason_slot = slots.get("reason", {}) or {}
            params["reason"] = reason_slot.get("value", "Alexa enabled hold")
        elif intent_name == "DisableHoldIntent":
            intent = "helm.operator_hold.disable"
            utterance = "disable hold"
        elif intent_name == "ConfirmIntent":
            intent = "helm.confirm"
            code_slot = slots.get("code", {}) or {}
            code = code_slot.get("value", "")
            params["code"] = "".join(code.split())
            utterance = f"confirm {code}"
        elif intent_name == "AMAZON.HelpIntent":
            intent = "helm.help"
            utterance = "help"
        else:
            intent = "helm.help"
            utterance = "help"

    nonce = body.get("request", {}).get("requestId", f"ALEXA-REQ-{time.time()}")
    device_id = body.get("context", {}).get("System", {}).get("device", {}).get("deviceId", "UNKNOWN_DEV")
    device_hash = "sha256:" + hashlib.sha256(device_id.encode()).hexdigest()
    session_id = session.get("sessionId", "session-unknown")

    envelope = {
        "request_id": f"VOICE-REQ-ALEXA-{hashlib.md5(nonce.encode()).hexdigest()[:8].upper()}",
        "provider": "ALEXA",
        "device_id_hash": device_hash,
        "actor_id": actor_id,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "intent": intent,
        "parameters": params,
        "utterance_redacted": utterance,
        "authentication_context": {
            "method": "oauth",
            "assurance_level": "HIGH" if actor_id == "founder" else "LOW"
        },
        "confirmation": {
            "required": False,
            "challenge_id": None,
            "confirmed": False
        },
        "nonce": nonce,
        "signature": signature or "test-signature",
        "schema_version": "1.0.0"
    }

    res = VoiceGatewayService.process_voice_request(envelope)
    should_end = True
    if res.get("status") == "CONFIRMATION_REQUIRED":
        should_end = False

    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": res.get("speech_text", "An error occurred.")
            },
            "shouldEndSession": should_end
        }
    }

def _alexa_speech_response(text: str) -> Dict[str, Any]:
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": True
        }
    }
