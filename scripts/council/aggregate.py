"""Post-validation success, quorum, aggregation, safety. Closes D-06, D-07, D-08, D-13, D-16, D-17."""
from __future__ import annotations

BLOCKING = {"BLOCKED", "BLOCKED_NO_QUORUM", "BLOCKED_PENDING_LIVE_PROOF", "DEGRADED_QUORUM",
            "INVALID_RESPONSE", "MODEL_MISMATCH", "EXECUTION_FAILURE", "UNKNOWN",
            "EVIDENCE_RECONCILIATION_REQUIRED"}

# --- execution modes -------------------------------------------------------
# The ONLY mode that can ever produce a live frontier quorum.
LIVE_EXTERNAL = "LIVE_EXTERNAL"
# Everything else is evidence about the harness, never about the council.
MOCK_INTERNAL = "MOCK_INTERNAL"
DRY_RUN = "DRY_RUN"
LOCAL_ONLY = "LOCAL_ONLY"

# Statuses that mock / dry-run evidence is ALLOWED to produce, and nothing more.
MOCK_ONLY_STATUS = "MOCK_FRONTIER_CONTRACT_PASS"
DRY_RUN_ONLY_STATUS = "DRY_RUN_PACKAGE_PASS"

FRONTIER_REQUIRED_PROVIDERS = 3
FRONTIER_REQUIRED_MEMBERS = 3


def frontier_live_quorum_evidence(profile_id, execution_mode, validation_results,
                                  authorization_consumed, run_id=None):
    """Every condition that must hold for a LIVE frontier quorum. Returns (ok, reasons).

    Absence of evidence is a FAILURE, never a pass.
    """
    reasons = []
    if profile_id != "frontier_council":
        reasons.append(f"PROFILE_NOT_FRONTIER:{profile_id}")
    if execution_mode != LIVE_EXTERNAL:
        reasons.append(f"EXECUTION_MODE_NOT_LIVE_EXTERNAL:{execution_mode}")
    if not authorization_consumed:
        reasons.append("AUTHORIZATION_NOT_CONSUMED")

    providers, members, run_ids = set(), set(), set()
    for mid, vr in (validation_results or {}).items():
        if not vr.get("accepted"):
            continue
        resp = vr.get("response") or {}
        tel = resp.get("telemetry") or {}
        if tel.get("is_fallback"):
            reasons.append(f"FALLBACK_RESPONSE_NOT_LIVE:{mid}")
            continue
        # A mock adapter must never be able to masquerade as a live provider.
        if tel.get("is_mock") or tel.get("adapter_kind") == "mock" or tel.get("simulated"):
            reasons.append(f"MOCK_RESPONSE_CANNOT_COUNT:{mid}")
            continue
        if not tel.get("raw_response_sha256") or not tel.get("raw_response_path"):
            reasons.append(f"NO_RAW_PROVIDER_BYTES:{mid}")
            continue
        if resp.get("provider_identity_source") != "provider_response":
            reasons.append(f"PROVIDER_IDENTITY_NOT_FROM_RESPONSE:{mid}")
            continue
        if resp.get("resolved_model_source") != "provider_response":
            reasons.append(f"RESOLVED_MODEL_NOT_FROM_RESPONSE:{mid}")
            continue
        providers.add(resp.get("provider"))
        members.add(mid)
        run_ids.add(resp.get("run_id"))

    if len(providers) < FRONTIER_REQUIRED_PROVIDERS:
        reasons.append(f"DISTINCT_PROVIDERS_{len(providers)}_LT_{FRONTIER_REQUIRED_PROVIDERS}")
    if len(members) < FRONTIER_REQUIRED_MEMBERS:
        reasons.append(f"DISTINCT_MEMBERS_{len(members)}_LT_{FRONTIER_REQUIRED_MEMBERS}")
    if len(run_ids) > 1:
        reasons.append(f"RUN_ID_DISAGREEMENT:{sorted(run_ids)}")
    if run_id and run_ids and run_ids != {run_id}:
        reasons.append("RUN_ID_NOT_AUTHORITATIVE")

    return (not reasons), reasons


def advisory_quorum(records, policy):
    """Advisory records are ADVISORY_ONLY. They can NEVER contribute to live quorum."""
    fresh = [r for r in records if r.get("status") == "RECORDED" and r.get("authority") == "ADVISORY_ONLY"]
    lanes = {}
    for r in fresh:
        lanes[r.get("lane")] = lanes.get(r.get("lane"), 0) + 1
    ok = len(fresh) >= policy["min_record_count"] and all(
        lanes.get(l, 0) >= n for l, n in policy["required_lane_distribution"].items())
    return {"advisory_records": len(fresh), "advisory_quorum_achieved": bool(ok),
            "authority": "ADVISORY_ONLY",
            "confers_live_authority": False,
            "note": "Advisory quorum cannot promote, unlock TRUE GO, or count as council liveness."}


def aggregate(registry, profile_id, dispatch_records, validation_results, advisory=None,
              execution_mode=MOCK_INTERNAL, authorization_consumed=False):
    """execution_mode is REQUIRED evidence, not decoration.

    Grok F1: frontier_council_quorum was derived from the PROFILE NAME alone, so three
    mock responses under profile=frontier_council produced frontier_council_quorum=true.
    Quorum now requires execution_mode == LIVE_EXTERNAL, and the default is MOCK_INTERNAL:
    a caller that forgets to declare its mode gets the SAFE answer, never the live one.
    """
    prof = registry.profile(profile_id)
    required = set(registry.required_ids(profile_id))
    enabled = registry.enabled()

    counts = {
        "configured_members": len(registry.seats),
        "enabled_members": len(enabled),
        "required_members": len(required),
        "advisory_records": (advisory or {}).get("advisory_records", 0),
        "dispatched_members": sum(1 for d in dispatch_records if d.get("dispatched")),
        "responded_members": len(validation_results),
        "validated_live_members": 0,
        "fallback_members": 0,
        "failed_members": 0,
        "quorum_eligible_members": 0,
    }

    live, dissent, failures, fallbacks = [], [], [], []
    for mid, vr in validation_results.items():
        t = (vr.get("response") or {}).get("telemetry", {}) or {}
        if not vr["accepted"]:
            counts["failed_members"] += 1
            failures.append({"member_id": mid, "status": vr.get("status", "FAILED_VISIBLE"),
                             "reasons": vr["reasons"]})
            continue
        if t.get("is_fallback"):
            counts["fallback_members"] += 1
            # a fallback is NEVER the original member's live success
            fallbacks.append({"original_member_id": t.get("fallback_from"),
                              "fallback_member_id": mid, "is_fallback": True,
                              "fallback_reason": t.get("fallback_reason")})
            continue
        counts["validated_live_members"] += 1
        seat = registry.get(mid)
        if seat["quorum_eligible"]:
            counts["quorum_eligible_members"] += 1
            live.append(mid)
        resp = vr["response"]
        if resp.get("verdict") in ("REJECT", "DISSENT") or resp.get("dissent"):
            dissent.append({"member_id": mid, "verdict": resp.get("verdict"),
                            "findings": resp.get("top_findings", [])})

    live_ids = set(live)
    missing_required = sorted(required - live_ids)
    # R2: profile-scoped quorum. There is NO generic "live_quorum" — that name was ambiguous
    # and let a local proof read as council liveness. Quorum is always named by its profile.
    profile_quorum = bool(required) and not missing_required and \
        len(live_ids) >= registry.min_quorum(profile_id)
    local_profile_quorum = bool(profile_quorum and profile_id == "local_proof")

    # R3 / Grok F1: frontier quorum is NOT a function of the profile name.
    # It requires LIVE_EXTERNAL execution, a consumed founder authorization, three
    # distinct providers, three distinct member IDs, raw provider bytes, and provider
    # identity + resolved model taken FROM the provider response.
    live_ok, live_reasons = frontier_live_quorum_evidence(
        profile_id, execution_mode, validation_results, authorization_consumed)
    frontier_council_quorum = bool(profile_quorum and live_ok)

    # HARD ASSERTION — the single line Grok asked for. Nothing below may re-enable it.
    if execution_mode != LIVE_EXTERNAL:
        frontier_council_quorum = False

    if failures and any(f["member_id"] in required for f in failures):
        status = "INVALID_RESPONSE"
    elif not live_ids:
        status = "BLOCKED_PENDING_LIVE_PROOF"
    elif missing_required:
        status = "BLOCKED_NO_QUORUM"
    elif not profile_quorum:
        status = "DEGRADED_QUORUM"
    elif dissent:
        status = "PASS_WITH_DISSENT"
    else:
        status = "PASS"

    # Mock / dry-run evidence may produce ONLY its own bounded status. It can never
    # produce PASS / FRONTIER_COUNCIL_PASS. This no longer depends on a mutable string
    # in frontier_seat_contracts.json (Grok F1 aggravating factor) -- it is driven by
    # execution_mode, which the caller must positively declare as LIVE_EXTERNAL.
    if profile_id == "frontier_council" and status in ("PASS", "PASS_WITH_DISSENT"):
        if execution_mode == MOCK_INTERNAL:
            status = MOCK_ONLY_STATUS
        elif execution_mode == DRY_RUN:
            status = DRY_RUN_ONLY_STATUS
        elif execution_mode != LIVE_EXTERNAL:
            status = "BLOCKED_PENDING_LIVE_PROOF"

    # local_proof can NEVER satisfy frontier quorum or promotion/release
    # Promotion requires FRONTIER quorum specifically. A local proof can never grant it.
    # A live quorum still does NOT imply promotion: promotion additionally requires a
    # promotion-capable profile, LIVE_EXTERNAL execution, and a consumed authorization.
    promotion_eligible = bool(prof["promotion_capable"] and frontier_council_quorum
                              and execution_mode == LIVE_EXTERNAL
                              and authorization_consumed
                              and status in ("PASS", "PASS_WITH_DISSENT"))
    release_eligible = bool(prof["release_capable"] and promotion_eligible)

    if profile_id == "local_proof" and status in ("PASS", "PASS_WITH_DISSENT"):
        status = "LOCAL_PROOF_PASS"

    # safe_to_execute_now requires FRONTIER quorum. LOCAL_PROOF_PASS is a real pass, but it
    # is NOT authorization to execute — it proves the harness, not the council.
    safe = bool(frontier_council_quorum and status in ("PASS", "PASS_WITH_DISSENT"))
    if (status in BLOCKING or not frontier_council_quorum
            or status in (MOCK_ONLY_STATUS, DRY_RUN_ONLY_STATUS)
            or execution_mode != LIVE_EXTERNAL
            or not authorization_consumed):
        safe = False

    return {
        "profile_id": profile_id,
        "execution_mode": execution_mode,
        "authorization_consumed": bool(authorization_consumed),
        "frontier_live_quorum_blocked_reasons": live_reasons,
        "overall_status": status,
        "counts": counts,
        "missing_required_members": missing_required,
        "quorum_required": registry.min_quorum(profile_id),
        "local_profile_quorum": local_profile_quorum,
        "frontier_council_quorum": frontier_council_quorum,
        "advisory_quorum": (advisory or {}).get("advisory_quorum_achieved", False),
        "advisory_confers_live_authority": False,
        "promotion_eligible": promotion_eligible,
        "release_eligible": release_eligible,
        "dissent": dissent,                 # preserved verbatim, never collapsed
        "fallbacks_used": fallbacks,        # every explicit fallback disclosed
        "failures": failures,
        "safe_to_execute_now": safe,        # BLOCKED => always False
        "registry_digest": registry.digest,
    }


def exit_code(agg, *, hold_restored, lock_clear, duplicate_processes, evidence_written,
              run_ids_consistent):
    """Nonzero on ANY integrity failure. 0 means the harness itself completed cleanly."""
    if not evidence_written:            return 5
    if not run_ids_consistent:          return 6
    if not hold_restored:               return 7
    if not lock_clear:                  return 8
    if duplicate_processes:             return 9
    if agg["failures"]:                 return 4
    if agg["missing_required_members"]: return 3
    if not (agg["local_profile_quorum"] or agg["frontier_council_quorum"]): return 2
    if agg["overall_status"] not in ("PASS", "PASS_WITH_DISSENT", "LOCAL_PROOF_PASS"): return 10
    return 0
