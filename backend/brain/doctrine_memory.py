import os
import yaml
import sqlite3
import logging
from datetime import datetime
from backend.brain.database import get_db_connection

logger = logging.getLogger("DoctrineMemory")

class DoctrineMemory:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.yaml_path = os.path.join(root_dir, "config/michael_doctrine.yaml")
        self.sync_yaml_to_db()

    def sync_yaml_to_db(self):
        # 1. Sync from seed yaml if available
        seed_path = os.path.join(self.root_dir, "config/michael_doctrine_seed.yaml")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if os.path.exists(seed_path):
                with open(seed_path, "r") as f:
                    seed_data = yaml.safe_load(f) or {}
                
                sections = [
                    ("doctrine", "core_rules"),
                    ("doctrine", "approval_preferences"),
                    ("doctrine", "escalation_required"),
                    ("doctrine", "blocked_actions"),
                    ("projects", "active_workstreams"),
                    ("projects", "recurring_workstreams"),
                    ("projects", "future_workstreams"),
                    ("autonomy", "modes"),
                    ("autonomy", "readiness_metrics"),
                    ("autonomy", "promotion_gates"),
                    ("qa", "required_gates"),
                    ("qa", "evidence_requirements"),
                    ("qa", "failure_rules")
                ]
                for parent, child in sections:
                    items = seed_data.get(parent, {}).get(child, [])
                    for index, item in enumerate(items):
                        rule_id = f"seed-{parent}-{child}-{index}"
                        rule_text = f"[{parent.upper()} - {child.replace('_', ' ').title()}] {item}"
                        cursor.execute("""
                            INSERT INTO doctrine_rules (id, rule_text, source, confidence, active, created_at)
                            VALUES (?, ?, 'seed', 1.0, 1, ?)
                            ON CONFLICT(id) DO UPDATE SET rule_text=excluded.rule_text, source='seed';
                        """, (rule_id, rule_text, datetime.utcnow().isoformat() + "Z"))
            
            # 2. Sync from traditional michael_doctrine.yaml if available
            if os.path.exists(self.yaml_path):
                with open(self.yaml_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                
                rules = data.get("michael_doctrine", {}).get("core_rules", [])
                for index, r in enumerate(rules):
                    rule_id = f"yaml-core-{index}"
                    cursor.execute("""
                        INSERT INTO doctrine_rules (id, rule_text, source, confidence, active, created_at)
                        VALUES (?, ?, 'yaml', 1.0, 1, ?)
                        ON CONFLICT(id) DO UPDATE SET rule_text=excluded.rule_text, source='yaml';
                    """, (rule_id, r, datetime.utcnow().isoformat() + "Z"))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to sync yaml doctrine to database: {e}")
        finally:
            conn.close()

    def get_all_rules(self) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, rule_text, source, confidence, active, created_at FROM doctrine_rules WHERE active = 1")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "ruleText": r[1],
                "source": r[2],
                "confidence": r[3],
                "active": bool(r[4]),
                "createdAt": r[5]
            }
            for r in rows
        ]

    def add_learned_rule(self, rule_text: str, source: str = "feedback", confidence: float = 0.8) -> str:
        import uuid
        rule_id = f"learned-{str(uuid.uuid4())[:8]}"
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO doctrine_rules (id, rule_text, source, confidence, active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (rule_id, rule_text, source, confidence, datetime.utcnow().isoformat() + "Z"))
            conn.commit()
            
            # Append to yaml config for local persistence
            self.append_rule_to_yaml(rule_text)
        except Exception as e:
            logger.error(f"Failed to save learned rule: {e}")
        finally:
            conn.close()
        return rule_id

    def append_rule_to_yaml(self, rule_text: str):
        if not os.path.exists(self.yaml_path):
            return
        try:
            with open(self.yaml_path, "r") as f:
                data = yaml.safe_load(f) or {}
            
            core_rules = data.setdefault("michael_doctrine", {}).setdefault("core_rules", [])
            if rule_text not in core_rules:
                core_rules.append(rule_text)
                
            with open(self.yaml_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Failed to append rule to yaml file: {e}")
