"""
HOCH Agent Swarm — Skill Registry Runtime Gate
Batch PR-4 / PERT P2 / GAP-003

Policy:
  - Fail-closed: unregistered skills are BLOCKED by default
  - BLOCKED risk_level: hard reject, no appeal path
  - HIGH risk_level: verdict = REQUIRES_APPROVAL
  - MEDIUM risk_level: ALLOWED if caller tier is permitted; rationale_required logged
  - LOW risk_level: ALLOWED if caller tier is permitted
  - Caller tier denied: DENIED (regardless of risk level)
  - Every evaluation is written to skill_audit SQLite DB

Endpoints wired in main.py:
  GET  /api/v1/skills/registry       — full registry
  GET  /api/v1/skills/registry/{id}  — single skill detail
  POST /api/v1/skills/evaluate       — evaluate invocation request
  GET  /api/v1/skills/audit-log      — evaluation history
  GET  /api/v1/skills/summary        — counts by risk_level / verdict
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE = Path(__file__).parent.parent
_REGISTRY_PATH = _BASE / "config" / "skill_registry.json"
_DB_PATH       = _BASE / "hoch_skill_audit.db"

# ── Verdicts ──────────────────────────────────────────────────────────────────
VERDICT_ALLOWED              = "ALLOWED"
VERDICT_REQUIRES_APPROVAL    = "REQUIRES_APPROVAL"
VERDICT_DENIED               = "DENIED"
VERDICT_BLOCKED              = "BLOCKED"
VERDICT_UNREGISTERED         = "UNREGISTERED"

# ── DB init ───────────────────────────────────────────────────────────────────
def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_audit (
            id            TEXT PRIMARY KEY,
            ts            REAL NOT NULL,
            skill_id      TEXT NOT NULL,
            skill_name    TEXT,
            caller_node   TEXT,
            caller_tier   TEXT,
            risk_level    TEXT,
            verdict       TEXT NOT NULL,
            reason        TEXT,
            rationale     TEXT,
            source        TEXT DEFAULT 'API'
        )
    """)
    conn.commit()
    return conn


# ── Registry loader (cached per process; reload on change) ────────────────────
_registry_cache: dict | None = None
_registry_mtime: float       = 0.0

def _load_registry() -> dict:
    global _registry_cache, _registry_mtime
    try:
        mtime = _REGISTRY_PATH.stat().st_mtime
        if _registry_cache is None or mtime != _registry_mtime:
            _registry_cache = json.loads(_REGISTRY_PATH.read_text())
            _registry_mtime = mtime
        return _registry_cache
    except Exception:
        return {}


def _skill_map() -> dict[str, dict]:
    reg = _load_registry()
    return {s["id"]: s for s in reg.get("skills", [])}


# ── Core gate logic ───────────────────────────────────────────────────────────
def evaluate_skill(
    skill_id: str,
    caller_tier: str,
    caller_node: str = "UNKNOWN",
    rationale: str   = "",
    source: str      = "API",
) -> dict[str, Any]:
    """
    Evaluate whether a skill invocation is permitted.

    Returns a dict with:
      verdict        — ALLOWED | REQUIRES_APPROVAL | DENIED | BLOCKED | UNREGISTERED
      skill_id       — echo of input
      skill_name     — display name from registry
      risk_level     — LOW | MEDIUM | HIGH | BLOCKED | (UNREGISTERED)
      reason         — human-readable explanation
      requires_rationale — bool
      requires_approval  — bool
      truth          — LIVE
    """
    skill_map = _skill_map()
    eval_id   = str(uuid.uuid4())[:8]
    ts        = time.time()

    if skill_id not in skill_map:
        _log_eval(eval_id, ts, skill_id, "UNKNOWN", caller_node, caller_tier,
                  "UNREGISTERED", VERDICT_UNREGISTERED,
                  "Skill not in registry — fail-closed rejection", rationale, source)
        return {
            "id":                   eval_id,
            "verdict":              VERDICT_UNREGISTERED,
            "skill_id":             skill_id,
            "skill_name":           None,
            "risk_level":           "UNREGISTERED",
            "reason":               "Skill not in registry. Fail-closed: BLOCKED.",
            "requires_rationale":   False,
            "requires_approval":    False,
            "truth":                "LIVE",
        }

    skill      = skill_map[skill_id]
    risk       = skill.get("risk_level", "HIGH")
    name       = skill.get("name", skill_id)
    allowed_t  = skill.get("allowed_caller_tiers", [])
    denied_t   = skill.get("denied_caller_tiers",  [])
    hard_block = skill.get("hard_reject", False)
    req_approv = skill.get("approval_required", False)
    req_ratio  = skill.get("rationale_required", False)

    # ── BLOCKED skills — hard reject, no appeal ───────────────────────────────
    if hard_block or risk == "BLOCKED":
        reason  = f"HARD BLOCKED skill — {skill.get('evidence','policy')}"
        verdict = VERDICT_BLOCKED
        _log_eval(eval_id, ts, skill_id, name, caller_node, caller_tier,
                  risk, verdict, reason, rationale, source)
        return _result(eval_id, verdict, skill_id, name, risk, reason, False, False)

    # ── Caller tier denied list ───────────────────────────────────────────────
    if caller_tier in denied_t:
        reason  = f"Caller tier {caller_tier!r} explicitly denied for {skill_id}"
        verdict = VERDICT_DENIED
        _log_eval(eval_id, ts, skill_id, name, caller_node, caller_tier,
                  risk, verdict, reason, rationale, source)
        return _result(eval_id, verdict, skill_id, name, risk, reason, False, False)

    # ── Caller tier not in allowed list ──────────────────────────────────────
    if allowed_t and caller_tier not in allowed_t:
        reason  = f"Caller tier {caller_tier!r} not in allowed list {allowed_t}"
        verdict = VERDICT_DENIED
        _log_eval(eval_id, ts, skill_id, name, caller_node, caller_tier,
                  risk, verdict, reason, rationale, source)
        return _result(eval_id, verdict, skill_id, name, risk, reason, False, False)

    # ── HIGH — requires operator approval ────────────────────────────────────
    if risk == "HIGH" or req_approv:
        reason  = f"HIGH-risk skill requires operator approval before execution"
        verdict = VERDICT_REQUIRES_APPROVAL
        _log_eval(eval_id, ts, skill_id, name, caller_node, caller_tier,
                  risk, verdict, reason, rationale, source)
        return _result(eval_id, verdict, skill_id, name, risk, reason, req_ratio, True)

    # ── MEDIUM — allowed but rationale logged ────────────────────────────────
    if risk == "MEDIUM":
        reason  = f"MEDIUM-risk skill allowed for tier {caller_tier}"
        verdict = VERDICT_ALLOWED
        _log_eval(eval_id, ts, skill_id, name, caller_node, caller_tier,
                  risk, verdict, reason, rationale, source)
        return _result(eval_id, verdict, skill_id, name, risk, reason, True, False)

    # ── LOW — allowed ─────────────────────────────────────────────────────────
    reason  = f"LOW-risk skill allowed for tier {caller_tier}"
    verdict = VERDICT_ALLOWED
    _log_eval(eval_id, ts, skill_id, name, caller_node, caller_tier,
              risk, verdict, reason, rationale, source)
    return _result(eval_id, verdict, skill_id, name, risk, reason, False, False)


def _result(
    eval_id: str, verdict: str, skill_id: str, name: str | None,
    risk: str, reason: str, req_ratio: bool, req_approv: bool,
) -> dict:
    return {
        "id":                  eval_id,
        "verdict":             verdict,
        "skill_id":            skill_id,
        "skill_name":          name,
        "risk_level":          risk,
        "reason":              reason,
        "requires_rationale":  req_ratio,
        "requires_approval":   req_approv,
        "truth":               "LIVE",
    }


def _log_eval(
    eval_id: str, ts: float, skill_id: str, name: str,
    caller_node: str, caller_tier: str,
    risk: str, verdict: str, reason: str, rationale: str, source: str,
) -> None:
    try:
        conn = _get_db()
        conn.execute(
            """INSERT INTO skill_audit
               (id, ts, skill_id, skill_name, caller_node, caller_tier,
                risk_level, verdict, reason, rationale, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (eval_id, ts, skill_id, name, caller_node, caller_tier,
             risk, verdict, reason, rationale or "", source),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never block the gate itself due to logging failure


# ── Public API helpers ────────────────────────────────────────────────────────
def get_registry_summary() -> dict:
    """Counts of skills by risk level, and a gate status report."""
    reg = _load_registry()
    skills = reg.get("skills", [])
    by_risk: dict[str, int] = {}
    for s in skills:
        rl = s.get("risk_level", "UNKNOWN")
        by_risk[rl] = by_risk.get(rl, 0) + 1

    return {
        "total_skills":  len(skills),
        "by_risk_level": by_risk,
        "blocked_count": by_risk.get("BLOCKED", 0),
        "high_count":    by_risk.get("HIGH",    0),
        "medium_count":  by_risk.get("MEDIUM",  0),
        "low_count":     by_risk.get("LOW",     0),
        "registry_loaded": _REGISTRY_PATH.exists(),
        "fail_closed":   True,
        "gate_status":   "ACTIVE" if _REGISTRY_PATH.exists() else "DEGRADED",
        "truth":         "LIVE",
    }


def get_audit_log(limit: int = 50, verdict_filter: str | None = None) -> dict:
    """Return skill evaluation history from the audit DB."""
    try:
        conn  = _get_db()
        query = "SELECT * FROM skill_audit"
        args: list = []
        if verdict_filter:
            query += " WHERE verdict = ?"
            args.append(verdict_filter)
        query += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)
        rows  = conn.execute(query, args).fetchall()
        conn.close()
        entries = [dict(r) for r in rows]
        # Verdict counts
        all_rows = conn.execute("SELECT verdict, COUNT(*) as c FROM skill_audit GROUP BY verdict") \
            if False else []  # already closed; handled below
        return {
            "entries": entries,
            "returned": len(entries),
            "limit": limit,
            "truth": "LIVE",
        }
    except Exception as exc:
        return {"entries": [], "returned": 0, "error": str(exc), "truth": "UNKNOWN"}


def get_audit_verdicts() -> dict:
    """Return verdict counts from audit DB."""
    try:
        conn  = _get_db()
        rows  = conn.execute(
            "SELECT verdict, COUNT(*) as c FROM skill_audit GROUP BY verdict"
        ).fetchall()
        conn.close()
        counts = {r["verdict"]: r["c"] for r in rows}
        return {
            "verdict_counts": counts,
            "total":          sum(counts.values()),
            "truth":          "LIVE",
        }
    except Exception:
        return {"verdict_counts": {}, "total": 0, "truth": "UNKNOWN"}
