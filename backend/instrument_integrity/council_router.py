import os
import json
import datetime
from pathlib import Path
from fastapi import APIRouter

# Make sure scripts directory is in sys.path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# Dynamically patch script modules if HELM_COUNCIL_DIR is in environment
import scripts.council.h1b_candidate_registry as h1b_reg
import scripts.council.h1_authorization as h1_auth

council_router = APIRouter()

@council_router.get("/api/v1/helm/council/state")
def get_council_state():
    # Authoritative council directory (sandbox via HELM_COUNCIL_DIR for tests)
    council_dir = (
        Path(os.environ["HELM_COUNCIL_DIR"])
        if os.environ.get("HELM_COUNCIL_DIR")
        else ROOT / "coordination" / "council"
    )
    packages_dir = council_dir / "live_proof_packages"

    # Patch registry/auth modules when sandboxed so package scans follow council_dir
    if os.environ.get("HELM_COUNCIL_DIR"):
        h1b_reg.PACKAGES_DIR = packages_dir
        if hasattr(h1b_reg, "ROSTER_PATH"):
            h1b_reg.ROSTER_PATH = council_dir / "council_roster.json"
        if hasattr(h1b_reg, "CONTRACTS_PATH"):
            h1b_reg.CONTRACTS_PATH = council_dir / "frontier_seat_contracts.json"
        h1_auth.COUNCIL_DIR = council_dir
        h1_auth.PACKAGES_DIR = packages_dir
        h1_auth.REGISTRY_PATH = council_dir / "h1_candidate_registry.json"
        h1_auth.ROSTER_PATH = council_dir / "council_roster.json"
        h1_auth.CONTRACTS_PATH = council_dir / "frontier_seat_contracts.json"

    observed_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    # Defaults (fail-closed)
    package_readiness = "UNKNOWN"
    quorum_readiness = "BLOCKED"
    promotion = "LOCKED"
    safe_to_execute = "NO"
    authorization_state = "UNKNOWN"
    evidence_state = "UNKNOWN"
    freshness_state = "UNKNOWN"
    reason = "Initialization fail-closed state"
    blocking_findings = []
    validated_at = None
    expires_at = None
    reconciliation = {}

    # Determine source revision (git HEAD; never invent success from REVISION file alone)
    source_revision = "UNKNOWN"
    try:
        import subprocess
        source_revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            text=True,
            timeout=5,
        ).strip()
    except Exception:
        try:
            rev_path = ROOT / "REVISION"
            if rev_path.exists():
                source_revision = rev_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    try:
        # 1. Evaluate Candidate Registry
        reconciliation = h1b_reg.reconcile_candidates()

        # Check operator hold
        operator_hold_active = True
        hold_path = ROOT / "has_live_project_tracker" / "data" / "ag_operator_hold.json"
        if hold_path.exists():
            try:
                hold_doc = json.loads(hold_path.read_text(encoding="utf-8"))
                # Support both schemas: operator_hold_active bool and operator_hold CLEAR
                if hold_doc.get("operator_hold_active") is False:
                    operator_hold_active = False
                if hold_doc.get("operator_hold") == "CLEAR":
                    operator_hold_active = False
            except Exception:
                pass
        if operator_hold_active:
            blocking_findings.append("OPERATOR_HOLD_ACTIVE")

        if reconciliation.get("status") == "RECONCILED":
            active_candidate = reconciliation.get("active_candidate")
            if active_candidate:
                integrity = reconciliation.get("integrity", {})
                if integrity.get("integrity_status") == "PASS":
                    package_readiness = "PASS"
                else:
                    package_readiness = "FAIL"
                    blocking_findings.append(f"PACKAGE_INTEGRITY_FAILED:{integrity.get('integrity_status')}")
            else:
                package_readiness = "FAIL"
                blocking_findings.append("NO_ACTIVE_CANDIDATE")
        else:
            package_readiness = "FAIL"
            blocking_findings.append(f"REGISTRY_UNRECONCILED:{reconciliation.get('reason')}")

        # 2. Evaluate Authorization State
        # Load h1b_founder_decision.json if exists
        decision_path = council_dir / "h1b_founder_decision.json"
        auth_id = None
        if decision_path.exists():
            try:
                decision = json.loads(decision_path.read_text(encoding="utf-8"))
                auth_id = decision.get("authorization_id")
                expires_at = decision.get("expires_at")

                # Check ledger
                from scripts.council.h1_authorization import AuthorizationLedger
                # If HELM_AUTH_LEDGER env var is present, it is automatically picked up
                ledger = AuthorizationLedger()
                if auth_id and ledger.is_consumed(auth_id):
                    authorization_state = "CONSUMED"
                else:
                    authorization_state = decision.get("authorization_status", "UNKNOWN")
            except Exception as e:
                authorization_state = "INVALID"
                blocking_findings.append(f"FOUNDER_DECISION_PARSE_ERROR:{e}")
        else:
            authorization_state = "UNKNOWN"
            blocking_findings.append("FOUNDER_DECISION_MISSING")

        # 3. Evaluate Live Provider Proof & Quorum
        live_state_path = council_dir / "council_live_state.json"
        if live_state_path.exists():
            try:
                live_state = json.loads(live_state_path.read_text(encoding="utf-8"))
                evidence_state = "PASS"

                # Check freshness
                completed_at_str = live_state.get("completed_at")
                if completed_at_str:
                    try:
                        completed_at = datetime.datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
                        now = datetime.datetime.now(datetime.timezone.utc)
                        age = (now - completed_at).total_seconds()
                        if age > 300:
                            freshness_state = "STALE"
                            blocking_findings.append("LIVE_PROOF_EVIDENCE_STALE")
                        else:
                            freshness_state = "FRESH"
                    except Exception:
                        freshness_state = "INVALID"
                        blocking_findings.append("LIVE_PROOF_TIMESTAMP_INVALID")
                else:
                    freshness_state = "UNKNOWN"
                    blocking_findings.append("LIVE_PROOF_TIMESTAMP_MISSING")

                # Quorum aggregation checks
                aggregation = live_state.get("aggregation", {})
                overall_status = aggregation.get("overall_status")
                frontier_council_quorum = aggregation.get("frontier_council_quorum", False)
                promotion_eligible = aggregation.get("promotion_eligible", False)
                safe_to_execute_now = aggregation.get("safe_to_execute_now", False)

                # Exclude mock evidence or any status that indicates mock/dry-run
                execution_mode = aggregation.get("execution_mode")
                if execution_mode != "LIVE_EXTERNAL":
                    blocking_findings.append(f"EXECUTION_MODE_NOT_LIVE_EXTERNAL:{execution_mode}")

                if freshness_state == "STALE":
                    quorum_readiness = "STALE"
                elif overall_status in ("PASS", "PASS_WITH_DISSENT") and frontier_council_quorum and freshness_state == "FRESH":
                    quorum_readiness = "PASS"
                    validated_at = completed_at_str
                elif overall_status in ("MOCK_FRONTIER_CONTRACT_PASS", "DRY_RUN_PACKAGE_PASS"):
                    quorum_readiness = "BLOCKED"
                    blocking_findings.append(f"QUORUM_CONTAINS_MOCK_EVIDENCE:{overall_status}")
                else:
                    quorum_readiness = "BLOCKED"
                    blocking_findings.append(f"QUORUM_STATUS_INVALID:{overall_status}")

                # Safe to execute check (requires PASS package, PASS quorum, consumed authorization, CLEAR hold)
                if (package_readiness == "PASS" and
                    quorum_readiness == "PASS" and
                    authorization_state == "CONSUMED" and
                    not operator_hold_active and
                    safe_to_execute_now):
                    safe_to_execute = "YES"
                else:
                    safe_to_execute = "NO"
                    if not safe_to_execute_now:
                        blocking_findings.append("NOT_SAFE_TO_EXECUTE_BY_HARNESS")
                    if authorization_state != "CONSUMED":
                        blocking_findings.append("AUTHORIZATION_NOT_CONSUMED")

                # Promotion check
                if (package_readiness == "PASS" and
                    quorum_readiness == "PASS" and
                    authorization_state == "CONSUMED" and
                    not operator_hold_active and
                    promotion_eligible):
                    promotion = "YES"
                else:
                    promotion = "LOCKED"
                    if not promotion_eligible:
                        blocking_findings.append("PROMOTION_NOT_ELIGIBLE_BY_HARNESS")

            except Exception as e:
                evidence_state = "INVALID"
                quorum_readiness = "BLOCKED"
                blocking_findings.append(f"LIVE_STATE_PARSE_ERROR:{e}")
        else:
            evidence_state = "UNKNOWN"
            quorum_readiness = "BLOCKED"
            blocking_findings.append("LIVE_PROOF_EVIDENCE_MISSING")

    except Exception as e:
        # Fatal path: revoke any partial success (fail-closed)
        reason = f"Fatal evaluation exception: {e}"
        blocking_findings.append(f"FATAL_EXCEPTION:{e}")
        package_readiness = "UNKNOWN"
        quorum_readiness = "BLOCKED"
        promotion = "LOCKED"
        safe_to_execute = "NO"
        if authorization_state in ("GRANTED", "CONSUMED"):
            authorization_state = "UNKNOWN"
        if evidence_state == "PASS":
            evidence_state = "UNKNOWN"

    # Set reason string based on findings
    if blocking_findings:
        reason = "Blocked by: " + ", ".join(blocking_findings)
    else:
        reason = "All gates verified and cleared"

    # Backward compatibility mappings (mirror authoritative fields; no READY synonym for PASS)
    h1_package_state = package_readiness
    h1_package_integrity = (
        (reconciliation or {}).get("integrity", {}).get("integrity_status", "UNKNOWN")
        if isinstance(reconciliation, dict)
        else "UNKNOWN"
    )

    try:
        matrix = h1b_reg.credential_matrix()
        openai_status = matrix.get("openai", {}).get("status")
        anthropic_status = matrix.get("anthropic", {}).get("status")
        xai_status = matrix.get("xai", {}).get("status")
        if openai_status == "PRESENT_UNVERIFIED" and anthropic_status == "PRESENT_UNVERIFIED" and xai_status == "PRESENT_UNVERIFIED":
            h1_credential_state = "PRESENT_UNVERIFIED"
        else:
            h1_credential_state = "NOT_PROVISIONED"
    except Exception:
        h1_credential_state = "UNKNOWN"

    h1_founder_authorization = authorization_state
    h1_live_provider_proof = evidence_state
    h1_frontier_live_quorum = quorum_readiness
    h1_promotion = promotion
    h1_safe_to_execute = safe_to_execute

    # H1C controlled activation truth (fail-closed; never invents founder grant)
    h1c = {}
    try:
        from backend.instrument_integrity.h1c_activation import compute_h1c_truth

        h1c = compute_h1c_truth(repo_root=ROOT, council_dir=council_dir)
        # Merge H1C blockers into findings (unique)
        for b in h1c.get("blockers") or []:
            if b not in blocking_findings:
                blocking_findings.append(b)
        # Promotion / safe_to_execute: H1C may only tighten, never loosen H1B locks
        if h1c.get("safe_to_execute") == "YES" and safe_to_execute == "YES":
            safe_to_execute = "YES"
        else:
            safe_to_execute = "NO"
            h1_safe_to_execute = "NO"
        if h1c.get("promotion") == "YES" and promotion == "YES":
            promotion = "YES"
        else:
            promotion = "LOCKED"
            h1_promotion = "LOCKED"
        if blocking_findings:
            reason = "Blocked by: " + ", ".join(blocking_findings)
    except Exception as e:
        h1c = {
            "overall_status": "ERROR",
            "blockers": [f"H1C_TRUTH_EXCEPTION:{type(e).__name__}"],
            "safe_to_execute": "NO",
            "promotion": "LOCKED",
        }
        safe_to_execute = "NO"
        promotion = "LOCKED"
        h1_safe_to_execute = "NO"
        h1_promotion = "LOCKED"
        blocking_findings.append(f"H1C_TRUTH_EXCEPTION:{type(e).__name__}")

    return {
        # Authoritative Contract Fields (H1B preserved)
        "package_readiness": package_readiness,
        "quorum_readiness": quorum_readiness,
        "promotion": promotion,
        "safe_to_execute": safe_to_execute,
        "authorization_state": authorization_state,
        "evidence_state": evidence_state,
        "freshness_state": freshness_state,
        "source_revision": source_revision,
        "observed_at": observed_at,
        "validated_at": validated_at,
        "expires_at": expires_at,
        "reason": reason,
        "blocking_findings": blocking_findings,

        # H1C normalized runtime truth
        "candidate_id": h1c.get("candidate_id"),
        "package_id": h1c.get("package_id"),
        "package_digest": h1c.get("package_digest"),
        "authorization_status": h1c.get("authorization_status", authorization_state),
        "operator_hold": h1c.get("operator_hold")
        or {
            "status": "UNKNOWN",
            "reason": "",
            "since": None,
            "release_eligible": False,
        },
        "live_proof": h1c.get("live_proof")
        or {
            "status": "UNKNOWN",
            "proof_id": None,
            "fresh": False,
            "age_seconds": None,
            "expires_at": None,
            "source_eligible": False,
        },
        "execution_scope": h1c.get("execution_scope") or [],
        "blockers": h1c.get("blockers") or blocking_findings,
        "truth_updated_at": h1c.get("truth_updated_at") or observed_at,
        "overall_status": h1c.get("overall_status") or "UNKNOWN",
        "h1c_state": h1c.get("h1c_state") or "UNKNOWN",
        "founder_action_required": h1c.get("founder_action_required", True),

        # Legacy/Test compatibility fields
        "h1_package_state": h1_package_state,
        "h1_package_integrity": h1_package_integrity,
        "h1_credential_state": h1_credential_state,
        "h1_founder_authorization": h1_founder_authorization,
        "h1_live_provider_proof": h1_live_provider_proof,
        "h1_frontier_live_quorum": h1_frontier_live_quorum,
        "h1_promotion": h1_promotion,
        "h1_safe_to_execute": h1_safe_to_execute,
    }
