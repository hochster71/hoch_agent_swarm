import hashlib
from datetime import datetime, timezone

def evaluate_gate_compliance(target_pod: str, results: dict) -> dict:
    # 1. Evaluate key metrics (e.g. check for failures, coverage)
    verdict = "APPROVED"
    reasons = []

    # Cyber scans check
    if target_pod == "cyber":
        vulnerabilities = results.get("critical_vulnerabilities", 0)
        if vulnerabilities > 0:
            verdict = "REJECTED"
            reasons.append(f"Found {vulnerabilities} critical vulnerabilities during gate sweep.")

    # Business checklist check
    if target_pod == "business":
        price_verified = results.get("price_matrix_verified", True)
        if not price_verified:
            verdict = "REJECTED"
            reasons.append("Price matrix validation failed.")

    # Generate authority sign-off hash
    timestamp = datetime.now(timezone.utc).isoformat()
    raw_signoff = f"gate_authority_verdict:{verdict}:{timestamp}:{target_pod}"
    signoff_hash = hashlib.sha256(raw_signoff.encode()).hexdigest()

    return {
        "verdict": verdict,
        "reasons": reasons if reasons else ["All boundary and compliance gates satisfied."],
        "evaluated_at": timestamp,
        "signoff_signature": f"gate_auth_sig_{signoff_hash[:16]}"
    }
