import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

# Naming conventions:
# Score Bands: GOLD (95-100), GREEN (85-94), AMBER (70-84), RED (50-69), BLACK (<50)
# Tiers: Tier 5: Lead Autonomous, Tier 4: Trusted Autonomous, Tier 3: Supervised, Tier 2: Restricted, Tier 1: Quarantined

TIERS_MAPPING = [
    {"name": "Tier 5: Lead Autonomous", "min": 95, "max": 100, "band": "GOLD", "priority": 0.95, "budget": "high"},
    {"name": "Tier 4: Trusted Autonomous", "min": 85, "max": 94, "band": "GREEN", "priority": 0.85, "budget": "standard"},
    {"name": "Tier 3: Supervised", "min": 70, "max": 84, "band": "AMBER", "priority": 0.70, "budget": "limited"},
    {"name": "Tier 2: Restricted", "min": 50, "max": 69, "band": "RED", "priority": 0.50, "budget": "none"},
    {"name": "Tier 1: Quarantined", "min": 0, "max": 49, "band": "BLACK", "priority": 0.0, "budget": "quarantined"}
]

ALLOWED_ACTIONS_BY_TIER = {
    "Tier 5: Lead Autonomous": ["own_mission_dag", "assign_responsible_agents", "recommend_go", "supervise_agents", "read", "analyze", "recommend", "run_tests", "write_patches", "create_evidence"],
    "Tier 4: Trusted Autonomous": ["execute_normal_tasks", "write_patches", "run_tests", "create_evidence", "propose_go", "read", "analyze", "recommend"],
    "Tier 3: Supervised": ["execute_bounded_tasks", "propose_fixes", "read", "analyze", "recommend", "run_tests"],
    "Tier 2: Restricted": ["read", "analyze", "diagnose", "propose_fixes"],
    "Tier 1: Quarantined": ["summarize", "explain", "produce_remediation_plans"]
}

RESTRICTED_ACTIONS_BY_TIER = {
    "Tier 5: Lead Autonomous": ["deploy", "merge_main", "change_secrets", "billing_access"],
    "Tier 4: Trusted Autonomous": ["own_mission_dag", "assign_responsible_agents", "supervise_agents", "deploy", "merge_main", "change_secrets", "billing_access"],
    "Tier 3: Supervised": ["mark_go", "approve_ui_release", "approve_security_work", "approve_release_work", "own_mission_dag", "assign_responsible_agents", "supervise_agents"],
    "Tier 2: Restricted": ["write_patches", "own_accountable_raci", "mark_go", "approve_ui_release", "approve_security_work", "approve_release_work"],
    "Tier 1: Quarantined": ["execute_tasks", "write_access", "mark_go", "propose_go", "own_accountable_raci"]
}

def init_accountability_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_trust_scores (
                agent_id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                trust_score INTEGER NOT NULL,
                trust_tier TEXT NOT NULL,
                band TEXT NOT NULL,
                routing_priority REAL NOT NULL,
                autonomy_budget TEXT NOT NULL,
                allowed_actions TEXT NOT NULL,
                restricted_actions TEXT NOT NULL,
                score_dimensions TEXT NOT NULL,
                reason TEXT,
                required_remedy TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_trust_ledger (
                record_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                mission_id TEXT,
                task_id TEXT,
                agent_id TEXT NOT NULL,
                raci_role TEXT,
                claim TEXT,
                actual_verdict TEXT,
                trust_score_before INTEGER,
                trust_score_after INTEGER,
                tier_before TEXT,
                tier_after TEXT,
                gate_results TEXT NOT NULL,
                objective_failures TEXT NOT NULL,
                policy_action TEXT NOT NULL,
                evidence TEXT NOT NULL
            )
        """)
        conn.commit()

        # Populate initial agents if empty
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM agent_trust_scores")
        if cur.fetchone()[0] == 0:
            initial_agents = [
                {
                    "agent_id": "qa-auditor-agent",
                    "agent_name": "QA Auditor Agent",
                    "trust_score": 72,
                    "reason": "Agent passed technical tests but missed operator access and visual parity defects.",
                    "required_remedy": "Cannot mark UI work GO until two consecutive screenshot-backed visual parity passes.",
                    "score_dimensions": {
                        "requirement_compliance": 70,
                        "evidence_quality": 82,
                        "test_accuracy": 74,
                        "false_go_rate": 40,
                        "operator_acceptance_rate": 55,
                        "regression_rate": 88,
                        "security_compliance": 95,
                        "raci_compliance": 80,
                        "visual_parity_accuracy": 35,
                        "access_validation_accuracy": 30
                    }
                },
                {
                    "agent_id": "monetization-compliance-agent",
                    "agent_name": "Monetization & Compliance Agent",
                    "trust_score": 90,
                    "reason": "High pricing validation accuracy.",
                    "required_remedy": "",
                    "score_dimensions": {
                        "requirement_compliance": 90,
                        "evidence_quality": 90,
                        "test_accuracy": 92,
                        "operator_acceptance_rate": 88,
                        "regression_rate": 95,
                        "raci_compliance": 90,
                        "security_compliance": 90,
                        "visual_parity_accuracy": 85,
                        "access_validation_accuracy": 85
                    }
                },
                {
                    "agent_id": "security-auditor-agent",
                    "agent_name": "Security Auditor Agent",
                    "trust_score": 95,
                    "reason": "Outstanding secrets scan and zero vulnerability leaks.",
                    "required_remedy": "",
                    "score_dimensions": {
                        "requirement_compliance": 95,
                        "evidence_quality": 95,
                        "test_accuracy": 98,
                        "operator_acceptance_rate": 96,
                        "regression_rate": 95,
                        "raci_compliance": 95,
                        "security_compliance": 100,
                        "visual_parity_accuracy": 90,
                        "access_validation_accuracy": 90
                    }
                },
                {
                    "agent_id": "hasf-pipeline-agent",
                    "agent_name": "HASF Pipeline Agent",
                    "trust_score": 88,
                    "reason": "Stable pipeline executions.",
                    "required_remedy": "",
                    "score_dimensions": {
                        "requirement_compliance": 88,
                        "evidence_quality": 85,
                        "test_accuracy": 90,
                        "operator_acceptance_rate": 90,
                        "regression_rate": 90,
                        "raci_compliance": 85,
                        "security_compliance": 90,
                        "visual_parity_accuracy": 80,
                        "access_validation_accuracy": 80
                    }
                },
                {
                    "agent_id": "live-tracker-runtime-agent",
                    "agent_name": "Live Tracker Runtime Agent",
                    "trust_score": 92,
                    "reason": "Excellent state synchronization and dashboard updates.",
                    "required_remedy": "",
                    "score_dimensions": {
                        "requirement_compliance": 92,
                        "evidence_quality": 90,
                        "test_accuracy": 92,
                        "operator_acceptance_rate": 95,
                        "regression_rate": 92,
                        "raci_compliance": 90,
                        "security_compliance": 95,
                        "visual_parity_accuracy": 90,
                        "access_validation_accuracy": 90
                    }
                }
            ]

            for a in initial_agents:
                score = a["trust_score"]
                # Map score to tier details
                tier_info = next((t for t in TIERS_MAPPING if t["min"] <= score <= t["max"]), TIERS_MAPPING[-1])
                tier_name = tier_info["name"]
                band = tier_info["band"]
                priority = tier_info["priority"]
                budget = tier_info["budget"]
                allowed = ALLOWED_ACTIONS_BY_TIER.get(tier_name, [])
                restricted = RESTRICTED_ACTIONS_BY_TIER.get(tier_name, [])

                cur.execute("""
                    INSERT INTO agent_trust_scores (
                        agent_id, agent_name, trust_score, trust_tier, band, routing_priority,
                        autonomy_budget, allowed_actions, restricted_actions, score_dimensions,
                        reason, required_remedy, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    a["agent_id"],
                    a["agent_name"],
                    score,
                    tier_name,
                    band,
                    priority,
                    budget,
                    json.dumps(allowed),
                    json.dumps(restricted),
                    json.dumps(a["score_dimensions"]),
                    a["reason"],
                    a["required_remedy"],
                    datetime.now(timezone.utc).isoformat() + "Z"
                ))
            conn.commit()
    finally:
        conn.close()

def get_all_agents():
    init_accountability_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM agent_trust_scores ORDER BY trust_score DESC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["allowed_actions"] = json.loads(d["allowed_actions"])
            d["restricted_actions"] = json.loads(d["restricted_actions"])
            d["score_dimensions"] = json.loads(d["score_dimensions"])
            result.append(d)
        return result
    finally:
        conn.close()

def get_agent(agent_id):
    init_accountability_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM agent_trust_scores WHERE agent_id = ?", (agent_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["allowed_actions"] = json.loads(d["allowed_actions"])
        d["restricted_actions"] = json.loads(d["restricted_actions"])
        d["score_dimensions"] = json.loads(d["score_dimensions"])
        return d
    finally:
        conn.close()

def get_ledger():
    init_accountability_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM agent_trust_ledger ORDER BY timestamp DESC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["gate_results"] = json.loads(d["gate_results"])
            d["objective_failures"] = json.loads(d["objective_failures"])
            d["policy_action"] = json.loads(d["policy_action"])
            d["evidence"] = json.loads(d["evidence"])
            result.append(d)
        return result
    finally:
        conn.close()

def add_ledger_entry(record_id, mission_id, task_id, agent_id, raci_role, claim, actual_verdict,
                     trust_score_before, trust_score_after, tier_before, tier_after,
                     gate_results, objective_failures, policy_action, evidence):
    init_accountability_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("""
            INSERT INTO agent_trust_ledger (
                record_id, timestamp, mission_id, task_id, agent_id, raci_role, claim, actual_verdict,
                trust_score_before, trust_score_after, tier_before, tier_after,
                gate_results, objective_failures, policy_action, evidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            datetime.now(timezone.utc).isoformat() + "Z",
            mission_id,
            task_id,
            agent_id,
            raci_role,
            claim,
            actual_verdict,
            trust_score_before,
            trust_score_after,
            tier_before,
            tier_after,
            json.dumps(gate_results),
            json.dumps(objective_failures),
            json.dumps(policy_action),
            json.dumps(evidence)
        ))
        conn.commit()
    finally:
        conn.close()

def update_agent_score(agent_id, score_dimensions=None, penalties_score=0, reason="", required_remedy=""):
    init_accountability_db()
    agent = get_agent(agent_id)
    if not agent:
        return None

    # Load scoring policy
    policy_path = Path("/Users/michaelhoch/hoch_agent_swarm/hoch_pods/accountability/policies/scoring_policy.json")
    if policy_path.exists():
        with open(policy_path, "r") as f:
            policy = json.load(f)
    else:
        policy = {
            "weights": {
                "requirement_compliance": 0.20,
                "evidence_quality": 0.15,
                "test_accuracy": 0.15,
                "operator_acceptance": 0.15,
                "regression_avoidance": 0.10,
                "raci_compliance": 0.10,
                "security_compliance": 0.10,
                "timeliness": 0.05
            }
        }

    # If score_dimensions updated, merge them
    current_dims = agent["score_dimensions"]
    if score_dimensions:
        for k, v in score_dimensions.items():
            if k in current_dims:
                current_dims[k] = v

    # Calculate weighted score
    w = policy["weights"]
    weighted_sum = 0.0
    weighted_sum += w.get("requirement_compliance", 0.20) * current_dims.get("requirement_compliance", 100)
    weighted_sum += w.get("evidence_quality", 0.15) * current_dims.get("evidence_quality", 100)
    weighted_sum += w.get("test_accuracy", 0.15) * current_dims.get("test_accuracy", 100)
    weighted_sum += w.get("operator_acceptance", 0.15) * current_dims.get("operator_acceptance_rate", current_dims.get("operator_acceptance", 100))
    weighted_sum += w.get("regression_avoidance", 0.10) * current_dims.get("regression_rate", 100)
    weighted_sum += w.get("raci_compliance", 0.10) * current_dims.get("raci_compliance", 100)
    weighted_sum += w.get("security_compliance", 0.10) * current_dims.get("security_compliance", 100)
    weighted_sum += w.get("timeliness", 0.05) * current_dims.get("timeliness", 100)

    # Substract penalties
    final_score = int(round(weighted_sum - penalties_score))
    final_score = max(0, min(100, final_score))

    # Map to new tier
    tier_info = next((t for t in TIERS_MAPPING if t["min"] <= final_score <= t["max"]), TIERS_MAPPING[-1])
    tier_name = tier_info["name"]
    band = tier_info["band"]
    priority = tier_info["priority"]
    budget = tier_info["budget"]
    allowed = ALLOWED_ACTIONS_BY_TIER.get(tier_name, [])
    restricted = RESTRICTED_ACTIONS_BY_TIER.get(tier_name, [])

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("""
            UPDATE agent_trust_scores SET
                trust_score = ?,
                trust_tier = ?,
                band = ?,
                routing_priority = ?,
                autonomy_budget = ?,
                allowed_actions = ?,
                restricted_actions = ?,
                score_dimensions = ?,
                reason = ?,
                required_remedy = ?,
                updated_at = ?
            WHERE agent_id = ?
        """, (
            final_score,
            tier_name,
            band,
            priority,
            budget,
            json.dumps(allowed),
            json.dumps(restricted),
            json.dumps(current_dims),
            reason or agent["reason"],
            required_remedy or agent["required_remedy"],
            datetime.now(timezone.utc).isoformat() + "Z",
            agent_id
        ))
        conn.commit()
    finally:
        conn.close()

    return get_agent(agent_id)
