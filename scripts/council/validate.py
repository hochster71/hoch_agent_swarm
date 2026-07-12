import datetime

def validate(
    resp: dict,
    active_run_id: str,
    active_profile_id: str,
    dispatched_member_id: str,
    registry: object,
    run_started_at: datetime.datetime,
    run_completed_at: datetime.datetime,
    seen_response_ids: set,
    seen_digests: set,
) -> tuple[bool, list[str]]:
    """Validate a provider response failing closed."""
    reasons = []
    
    try:
        telemetry = resp.get("telemetry", {})
        if not telemetry:
            reasons.append("Missing telemetry in response")
            return False, reasons
            
        if telemetry.get("run_id") != active_run_id:
            reasons.append(f"run_id mismatch: expected {active_run_id}, got {telemetry.get('run_id')}")
            
        if telemetry.get("profile_id") != active_profile_id:
            reasons.append(f"profile_id mismatch: expected {active_profile_id}, got {telemetry.get('profile_id')}")
            
        if telemetry.get("member_id") != dispatched_member_id:
            reasons.append(f"member_id mismatch: expected {dispatched_member_id}, got {telemetry.get('member_id')}")
            
        response_id = telemetry.get("response_id")
        if not response_id:
            reasons.append("Missing response_id")
        elif response_id in seen_response_ids:
            reasons.append(f"Duplicate response_id: {response_id}")
        else:
            seen_response_ids.add(response_id)
            
        digest = telemetry.get("response_digest")
        if not digest:
            reasons.append("Missing response_digest")
        elif digest in seen_digests:
            reasons.append(f"Duplicate response_digest (replay detected): {digest}")
        else:
            seen_digests.add(digest)

        if not telemetry.get("provider"):
            reasons.append("Missing provider identity")
            
        return len(reasons) == 0, reasons
        
    except Exception as e:
        reasons.append(f"Validation exception: {e}")
        return False, reasons
