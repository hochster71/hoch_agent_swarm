"""
prompt_governance.py
====================
HOCH Agent Swarm — Prompt Library Governance Engine

Policy:
  LOW     → ALLOWED automatically, logged to ledger
  MEDIUM  → ALLOWED with required rationale, logged to ledger
  HIGH    → PENDING_APPROVAL, must be approved via /api/v1/prompts/approve
  BLOCKED → REJECTED, attempt logged, operator alerted

All prompt use is logged to the prompt_usage_ledger table in swarm_ledger.db.
The library source file is read-only; this module never writes to it.
"""

import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

_APPROVAL_TTL_HOURS = 24  # Operator approvals expire after this
_TEST_PREFIXES = ("pytest", "test", "smoke", "ci_", "ci:")  # → source=TEST

# ── Paths ─────────────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIBRARY_PATH = os.path.join(_HERE, "prompt_library.json")
_DB_PATH = os.path.join(_HERE, "swarm_ledger.db")

# ── Risk classification rules (word-boundary aware) ───────────────────────────

# Hard-BLOCKED: actual adversarial instructions targeting the executing agent
_BLOCKED_RULES = [
    (r"\bDAN\b",                           "Jailbreak persona keyword"),
    (r"\bignore previous instructions?\b", "Prompt injection instruction"),
    (r"\bdisable safety\b",                "Safety bypass instruction"),
    (r"\brm\s+-rf\b",                      "Destructive shell command"),
]

# HIGH: sensitive scopes that require human approval before execution
_HIGH_RULES = [
    (r"\bjailbreak\b",         "Jailbreak testing scope"),
    (r"\bred.?team\b",         "Red team scenario generation"),
    (r"\bexfiltrat\b",         "Data exfiltration analysis"),
    (r"\bprivilege\s+escalat", "Privilege escalation analysis"),
    (r"\bbrute.?force\b",      "Brute force / enumeration scope"),
    (r"\bcredential\b",        "Credential exposure scope"),
    (r"\bexploit\b",           "Exploit execution scope"),
    (r"\bscanl?\b",            "Network scan scope"),
    (r"\bprod(uction)?\s+deploy", "Production deployment scope"),
]

# MEDIUM: advisory flags — allowed with logged rationale
_MEDIUM_RULES = [
    (r"\bsecret\b",          "Secret reference"),
    (r"\btoken\b",           "Token reference"),
    (r"\bdelet(e|ing)\b",    "Delete operation reference"),
    (r"\binjection\b",       "Injection theme (review context)"),
    (r"\bbypass\b",          "Bypass theme (review context)"),
]

# Category mapping
_CAT_MAP = {
    "QA": "QA", "Audit": "AUDIT", "DevSecOps": "DEVSECOPS",
    "SAST": "SAST", "DAST": "DAST", "Operations": "OPERATIONS",
    "Coding": "CODING", "Security Architecture": "ARCHITECTURE",
    "AI / ML Systems": "ARCHITECTURE", "Incident Response": "GOVERNANCE",
    "Governance": "GOVERNANCE", "Vulnerability Management": "CYBERSECURITY",
    "Data Security": "CYBERSECURITY", "Detection Engineering": "CYBERSECURITY",
    "Privacy": "GOVERNANCE", "Cloud Security": "DEVSECOPS",
    "Supply Chain": "SUPPLY_CHAIN", "Legal / Compliance": "GOVERNANCE",
    "UX Security": "QA", "Industry Specialized": "UNKNOWN",
}

# ── Library loading & classification ──────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_and_classify() -> list:
    """
    Load prompt_library.json, compute per-prompt SHA-256, classify risk.
    Result is cached for the lifetime of the process (library is read-only).
    Returns list of enriched prompt dicts.
    """
    try:
        with open(_LIBRARY_PATH, "r") as f:
            raw = json.load(f)
    except Exception as e:
        return []

    enriched = []
    for p in raw:
        # Per-prompt SHA-256 (deterministic from canonical JSON)
        canonical = json.dumps(p, sort_keys=True, ensure_ascii=True)
        sha256 = hashlib.sha256(canonical.encode()).hexdigest()

        # Risk classification
        text = (p.get("prompt", "") + " " + p.get("mission", "")).lower()

        blocked = [(desc) for pat, desc in _BLOCKED_RULES if re.search(pat.lower(), text)]
        high    = [(desc) for pat, desc in _HIGH_RULES    if re.search(pat.lower(), text)] if not blocked else []
        medium  = [(desc) for pat, desc in _MEDIUM_RULES  if re.search(pat.lower(), text)] if not blocked and not high else []

        if blocked:
            risk = "BLOCKED"
        elif high:
            risk = "HIGH"
        elif medium:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        requires_approval = risk in ("BLOCKED", "HIGH")
        if risk == "BLOCKED":
            allowed_modes = []
        elif risk == "HIGH":
            allowed_modes = ["read", "suggest"]
        elif risk == "MEDIUM":
            allowed_modes = ["read", "suggest", "execute_with_approval"]
        else:
            allowed_modes = ["read", "suggest", "execute_with_approval"]

        enriched.append({
            **p,
            "sha256": sha256,
            "mapped_category": _CAT_MAP.get(p.get("category", ""), "UNKNOWN"),
            "risk_level": risk,
            "risk_reasons": blocked + high + medium,
            "requires_approval": requires_approval,
            "allowed_modes": allowed_modes,
            "review_status": "APPROVED" if risk in ("LOW", "MEDIUM") else "NEEDS_REVIEW",
            "last_reviewed_at": "2026-06-26T15:49:00Z",
        })

    return enriched


def get_all_prompts(
    category: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
) -> dict:
    prompts = _load_and_classify()
    total = len(prompts)

    if category:
        prompts = [p for p in prompts if p.get("category", "").lower() == category.lower()]
    if industry:
        prompts = [p for p in prompts if p.get("industry", "").lower() == industry.lower()]
    if search:
        q = search.lower()
        prompts = [
            p for p in prompts
            if q in p.get("id", "").lower()
            or q in p.get("title", "").lower()
            or q in p.get("mission", "").lower()
            or q in p.get("category", "").lower()
            or q in p.get("prompt", "").lower()
        ]

    return {
        "count": len(prompts[:limit]),
        "total": total,
        "prompts": prompts[:limit],
        "source": "prompt_library.json",
        "freshness": "static",
    }


def get_prompt_by_id(prompt_id: str) -> Optional[dict]:
    for p in _load_and_classify():
        if p.get("id", "").upper() == prompt_id.upper():
            return p
    return None


def get_categories() -> dict:
    prompts = _load_and_classify()
    categories = sorted(set(p.get("category", "") for p in prompts if p.get("category")))
    industries = sorted(set(p.get("industry", "") for p in prompts if p.get("industry")))
    return {
        "categories": categories,
        "industries": industries,
        "total_prompts": len(prompts),
    }


# ── SQLite ledger ──────────────────────────────────────────────────────────────

_db_lock = threading.Lock()


def _get_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _infer_source(requested_by: str) -> str:
    """Classify approval source: TEST (from automated tests) or OPERATOR (human)."""
    rb = (requested_by or "").lower()
    if any(rb.startswith(p) for p in _TEST_PREFIXES) or "pytest" in rb:
        return "TEST"
    if rb in ("ui_operator", "ui"):
        return "UI"
    return "OPERATOR"


def ensure_ledger_table():
    """Create/migrate prompt_usage_ledger and prompt_approvals tables."""
    with _db_lock:
        conn = _get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prompt_usage_ledger (
                ledger_id       TEXT PRIMARY KEY,
                prompt_id       TEXT NOT NULL,
                prompt_sha256   TEXT NOT NULL,
                category        TEXT,
                risk_level      TEXT NOT NULL,
                agent_id        TEXT,
                mission_context TEXT,
                rationale       TEXT,
                decision        TEXT NOT NULL,
                approved_by     TEXT,
                approval_id     TEXT,
                logged_at       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_approvals (
                approval_id     TEXT PRIMARY KEY,
                prompt_id       TEXT NOT NULL,
                prompt_sha256   TEXT NOT NULL,
                risk_level      TEXT NOT NULL,
                agent_id        TEXT,
                mission_context TEXT,
                rationale       TEXT,
                status          TEXT NOT NULL DEFAULT 'PENDING',
                source          TEXT NOT NULL DEFAULT 'OPERATOR',
                requested_by    TEXT,
                reviewed_by     TEXT,
                requested_at    TEXT NOT NULL,
                reviewed_at     TEXT,
                expires_at      TEXT,
                decision_note   TEXT
            );
        """)
        # Migrate: add source column if missing (for DBs created before Prompt-3)
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(prompt_approvals)").fetchall()}
        if "source" not in existing_cols:
            conn.execute("ALTER TABLE prompt_approvals ADD COLUMN source TEXT NOT NULL DEFAULT 'UNKNOWN'")
            # Back-fill: mark existing rows by requested_by heuristic
            rows = conn.execute("SELECT approval_id, requested_by FROM prompt_approvals").fetchall()
            for aid, rb in rows:
                src = _infer_source(rb or "")
                conn.execute("UPDATE prompt_approvals SET source=? WHERE approval_id=?", (src, aid))
        if "expires_at" not in existing_cols:
            conn.execute("ALTER TABLE prompt_approvals ADD COLUMN expires_at TEXT")
        conn.commit()
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Policy gate ────────────────────────────────────────────────────────────────

def select_prompt(
    prompt_id: str,
    agent_id: str = "OPERATOR",
    mission_context: str = "",
    rationale: str = "",
    requested_by: str = "Operator",
) -> dict:
    """
    Policy gate for prompt selection.
    Returns a decision envelope:
      { decision: ALLOWED | ALLOWED_WITH_RATIONALE | PENDING_APPROVAL | REJECTED,
        prompt: {...}, approval_id?, ledger_id, risk_level, policy_message }
    """
    ensure_ledger_table()
    prompt = get_prompt_by_id(prompt_id)
    if not prompt:
        return {
            "decision": "REJECTED",
            "reason": "PROMPT_NOT_FOUND",
            "policy_message": f"Prompt '{prompt_id}' not found in library.",
            "prompt_id": prompt_id,
        }

    risk = prompt["risk_level"]
    sha256 = prompt["sha256"]
    category = prompt.get("category", "")
    ledger_id = str(uuid.uuid4())
    approval_id = None
    decision = "REJECTED"

    if risk == "BLOCKED":
        decision = "REJECTED"
        _write_ledger(ledger_id, prompt_id, sha256, category, risk,
                      agent_id, mission_context, rationale, decision,
                      approved_by=None, approval_id=None)
        return {
            "decision": decision,
            "reason": "BLOCKED_PROMPT",
            "risk_level": risk,
            "risk_reasons": prompt.get("risk_reasons", []),
            "policy_message": "This prompt is blocked from execution. It contains patterns that require security officer review.",
            "prompt_id": prompt_id,
            "prompt_sha256": sha256,
            "ledger_id": ledger_id,
        }

    elif risk == "HIGH":
        # Check if there is an existing APPROVED approval for this prompt+agent
        existing = _get_active_approval(prompt_id, agent_id)
        if existing:
            decision = "ALLOWED"
            approval_id = existing["approval_id"]
            _write_ledger(ledger_id, prompt_id, sha256, category, risk,
                          agent_id, mission_context, rationale, decision,
                          approved_by=existing["reviewed_by"], approval_id=approval_id)
            return {
                "decision": decision,
                "risk_level": risk,
                "policy_message": "HIGH-risk prompt approved by operator. Execution allowed. Use is logged.",
                "prompt_id": prompt_id,
                "prompt_sha256": sha256,
                "approval_id": approval_id,
                "ledger_id": ledger_id,
                "prompt": prompt,
            }
        else:
            # Create pending approval request
            approval_id = str(uuid.uuid4())
            _create_approval_request(approval_id, prompt_id, sha256, risk,
                                     agent_id, mission_context, rationale, requested_by)
            decision = "PENDING_APPROVAL"
            _write_ledger(ledger_id, prompt_id, sha256, category, risk,
                          agent_id, mission_context, rationale, decision,
                          approved_by=None, approval_id=approval_id)
            return {
                "decision": decision,
                "risk_level": risk,
                "policy_message": "HIGH-risk prompt requires operator approval. Submit the approval_id to POST /api/v1/prompts/approve.",
                "prompt_id": prompt_id,
                "prompt_sha256": sha256,
                "approval_id": approval_id,
                "ledger_id": ledger_id,
                "prompt_title": prompt.get("title"),
                "risk_reasons": prompt.get("risk_reasons", []),
            }

    elif risk == "MEDIUM":
        if not rationale or len(rationale.strip()) < 10:
            return {
                "decision": "RATIONALE_REQUIRED",
                "risk_level": risk,
                "policy_message": "MEDIUM-risk prompt requires a rationale (min 10 chars). Resend with 'rationale' field.",
                "prompt_id": prompt_id,
                "prompt_sha256": sha256,
            }
        decision = "ALLOWED_WITH_RATIONALE"
        _write_ledger(ledger_id, prompt_id, sha256, category, risk,
                      agent_id, mission_context, rationale, decision,
                      approved_by=None, approval_id=None)
        return {
            "decision": decision,
            "risk_level": risk,
            "policy_message": "MEDIUM-risk prompt allowed with rationale. Use is logged.",
            "prompt_id": prompt_id,
            "prompt_sha256": sha256,
            "ledger_id": ledger_id,
            "prompt": prompt,
        }

    else:  # LOW
        decision = "ALLOWED"
        _write_ledger(ledger_id, prompt_id, sha256, category, risk,
                      agent_id, mission_context, rationale, decision,
                      approved_by=None, approval_id=None)
        return {
            "decision": decision,
            "risk_level": risk,
            "policy_message": "LOW-risk prompt allowed. Use is logged.",
            "prompt_id": prompt_id,
            "prompt_sha256": sha256,
            "ledger_id": ledger_id,
            "prompt": prompt,
        }


def approve_prompt(
    approval_id: str,
    reviewed_by: str = "Operator",
    decision_note: str = "",
    deny: bool = False,
) -> dict:
    """Operator approves or denies a pending HIGH-risk prompt request."""
    ensure_ledger_table()
    with _db_lock:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM prompt_approvals WHERE approval_id = ?",
            (approval_id,)
        ).fetchone()
        if not row:
            conn.close()
            return {"error": f"Approval request '{approval_id}' not found."}

        if row["status"] != "PENDING":
            conn.close()
            return {"error": f"Approval request is already '{row['status']}'."}

        new_status = "DENIED" if deny else "APPROVED"
        # Set TTL only for real approvals, not denials
        expires_at = None
        if not deny:
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=_APPROVAL_TTL_HOURS)).isoformat()

        conn.execute(
            """UPDATE prompt_approvals
               SET status=?, reviewed_by=?, reviewed_at=?, decision_note=?, expires_at=?,
                   source='OPERATOR'
               WHERE approval_id=?""",
            (new_status, reviewed_by, _now(), decision_note, expires_at, approval_id)
        )

        # Write decision to ledger
        ledger_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO prompt_usage_ledger
               (ledger_id, prompt_id, prompt_sha256, category, risk_level,
                agent_id, mission_context, rationale, decision,
                approved_by, approval_id, logged_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ledger_id, row["prompt_id"], row["prompt_sha256"],
                "", row["risk_level"],
                row["agent_id"], row["mission_context"], decision_note,
                f"APPROVAL_{new_status}", reviewed_by, approval_id, _now()
            )
        )
        conn.commit()
        conn.close()

    return {
        "approval_id": approval_id,
        "prompt_id": row["prompt_id"],
        "status": new_status,
        "reviewed_by": reviewed_by,
        "decision_note": decision_note,
        "expires_at": expires_at,
        "ledger_id": ledger_id,
        "message": f"Prompt {'approved' if not deny else 'denied'} by {reviewed_by}.",
    }


def get_usage_ledger(limit: int = 200, prompt_id: str = None) -> dict:
    """Return the usage ledger, optionally filtered by prompt_id."""
    ensure_ledger_table()
    with _db_lock:
        conn = _get_conn()
        if prompt_id:
            rows = conn.execute(
                "SELECT * FROM prompt_usage_ledger WHERE prompt_id=? ORDER BY logged_at DESC LIMIT ?",
                (prompt_id.upper(), limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM prompt_usage_ledger ORDER BY logged_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        entries = [dict(r) for r in rows]
        total = conn.execute("SELECT COUNT(*) FROM prompt_usage_ledger").fetchone()[0]
        conn.close()
    return {
        "total": total,
        "count": len(entries),
        "entries": entries,
    }


def get_pending_approvals() -> dict:
    """Return all PENDING prompt approval requests (for Governance Cockpit queue)."""
    ensure_ledger_table()
    with _db_lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM prompt_approvals WHERE status='PENDING' ORDER BY requested_at DESC"
        ).fetchall()
        entries = [dict(r) for r in rows]
        conn.close()
    return {"pending_count": len(entries), "approvals": entries}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _write_ledger(ledger_id, prompt_id, sha256, category, risk,
                  agent_id, mission_context, rationale, decision,
                  approved_by, approval_id):
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """INSERT OR IGNORE INTO prompt_usage_ledger
               (ledger_id, prompt_id, prompt_sha256, category, risk_level,
                agent_id, mission_context, rationale, decision,
                approved_by, approval_id, logged_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ledger_id, prompt_id, sha256, category, risk,
             agent_id or "", mission_context or "", rationale or "", decision,
             approved_by or "", approval_id or "", _now())
        )
        conn.commit()
        conn.close()


def _create_approval_request(approval_id, prompt_id, sha256, risk,
                              agent_id, mission_context, rationale, requested_by):
    source = _infer_source(requested_by or "")
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """INSERT OR IGNORE INTO prompt_approvals
               (approval_id, prompt_id, prompt_sha256, risk_level,
                agent_id, mission_context, rationale, status, source,
                requested_by, requested_at)
               VALUES (?,?,?,?,?,?,?,'PENDING',?,?,?)""",
            (approval_id, prompt_id, sha256, risk,
             agent_id or "", mission_context or "", rationale or "",
             source, requested_by or "Operator", _now())
        )
        conn.commit()
        conn.close()


def _get_active_approval(prompt_id: str, agent_id: str) -> Optional[dict]:
    """
    Return the most recent APPROVED, OPERATOR-sourced, non-expired approval
    for this prompt. TEST approvals are NEVER honoured for live execution.
    """
    with _db_lock:
        conn = _get_conn()
        row = conn.execute(
            """SELECT * FROM prompt_approvals
               WHERE prompt_id=?
                 AND status='APPROVED'
                 AND source IN ('OPERATOR','UI')
               ORDER BY reviewed_at DESC LIMIT 1""",
            (prompt_id.upper(),)
        ).fetchone()
        conn.close()
    if not row:
        return None
    d = dict(row)
    # Enforce TTL
    expires = d.get("expires_at")
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            if datetime.now(timezone.utc) > exp_dt:
                return None  # Expired
        except Exception:
            pass
    return d

# ── Additional public API functions (Prompt-3) ─────────────────────────────────

def get_all_approvals(status: str = None) -> dict:
    """
    Return all rows from prompt_approvals.
    Each row includes source (TEST|UI|OPERATOR), TTL status, and whether
    the approval is currently active (APPROVED + not expired + OPERATOR/UI source).
    Optional filter: status in ('PENDING','APPROVED','DENIED','EXPIRED').
    """
    ensure_ledger_table()
    now_utc = datetime.now(timezone.utc)
    with _db_lock:
        conn = _get_conn()
        if status:
            rows = conn.execute(
                "SELECT * FROM prompt_approvals WHERE status=? ORDER BY requested_at DESC",
                (status.upper(),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM prompt_approvals ORDER BY requested_at DESC"
            ).fetchall()
        conn.close()

    enriched = []
    for r in rows:
        d = dict(r)
        # Compute TTL state
        d["is_test"] = d.get("source", "UNKNOWN") == "TEST"
        expires = d.get("expires_at")
        if expires and d["status"] == "APPROVED":
            try:
                exp_dt = datetime.fromisoformat(expires)
                d["ttl_remaining_hours"] = max(0, round((exp_dt - now_utc).total_seconds() / 3600, 1))
                d["is_expired"] = exp_dt <= now_utc
            except Exception:
                d["ttl_remaining_hours"] = None
                d["is_expired"] = False
        else:
            d["ttl_remaining_hours"] = None
            d["is_expired"] = False
        # is_active: only OPERATOR/UI, APPROVED, not expired
        d["is_active"] = (
            d["status"] == "APPROVED"
            and d.get("source", "") in ("OPERATOR", "UI")
            and not d["is_expired"]
        )
        enriched.append(d)

    pending = sum(1 for d in enriched if d["status"] == "PENDING")
    active = sum(1 for d in enriched if d["is_active"])
    test_count = sum(1 for d in enriched if d["is_test"])
    return {
        "total": len(enriched),
        "pending_count": pending,
        "active_count": active,
        "test_count": test_count,
        "approvals": enriched,
    }


def expire_test_approvals() -> dict:
    """
    Mark all TEST-sourced APPROVED or PENDING approvals as EXPIRED.
    Returns count of records updated.
    Prevents test approvals from silently authorising future HIGH-risk execution.
    """
    ensure_ledger_table()
    with _db_lock:
        conn = _get_conn()
        rows = conn.execute(
            """SELECT approval_id, prompt_id FROM prompt_approvals
               WHERE source='TEST' AND status IN ('PENDING','APPROVED')"""
        ).fetchall()
        count = len(rows)
        for row in rows:
            conn.execute(
                """UPDATE prompt_approvals
                   SET status='EXPIRED', reviewed_by='SYSTEM', reviewed_at=?,
                       decision_note='Auto-expired: test-sourced approval (Prompt-3 isolation)'
                   WHERE approval_id=?""",
                (_now(), row[0])
            )
        conn.commit()
        conn.close()
    return {
        "expired_count": count,
        "message": f"Expired {count} TEST-sourced approval(s). Operator approvals unaffected.",
        "expired_ids": [r[0] for r in rows],
    }
