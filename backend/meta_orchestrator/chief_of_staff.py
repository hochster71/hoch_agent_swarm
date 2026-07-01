import os
import datetime
from typing import Dict, List, Any
from backend.meta_orchestrator.domain_registry import DomainRegistry
from backend.meta_orchestrator.coverage_matrix import CoverageMatrix
from backend.meta_orchestrator.omission_detector import OmissionDetector
from backend.meta_orchestrator.decision_queue import DecisionQueue
from backend.meta_orchestrator.daily_autonomy_brief import DailyAutonomyBrief
from backend.meta_orchestrator.escalation_router import EscalationRouter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "backend/db/swarm_ledger.db")

class ChiefOfStaff:
    def __init__(self):
        self.registry = DomainRegistry()
        self.coverage = CoverageMatrix(self.registry)
        self.detector = OmissionDetector(PROJECT_ROOT)
        self.queue = DecisionQueue(DB_PATH)
        self.brief_compiler = DailyAutonomyBrief()
        self.escalator = EscalationRouter()

    def run_autonomy_loop(self) -> Dict[str, Any]:
        # 1. Run omission gap scan
        gaps = self.detector.run_all_scans()

        # 2. Assign ownerless domains dynamically if flagged
        metrics = self.coverage.compute_metrics()
        
        # 3. Handle escalations based on gap severity
        for gap in gaps:
            if self.escalator.evaluate_escalation(gap):
                # Add to operator decision queue
                decision_id = f"escalation_{gap['category']}_{gap['target'].replace('/', '_').replace('.', '_')}"
                self.queue.add_decision(
                    decision_id,
                    f"Resolve Gap in {gap['category']}: {gap['target']}",
                    gap["description"],
                    gap["category"],
                    gap["severity"]
                )

        # 4. Calculate final orchestration load & brief
        load_score = self.queue.compute_orchestration_load()
        metrics["michael_orchestration_load"] = load_score

        decisions = self.queue.get_pending_decisions()
        brief_md = self.brief_compiler.compile_brief(metrics, gaps, decisions)
        matrix_md = self.coverage.generate_matrix_markdown()

        # 5. Write evidence logs
        ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
        evidence_dir = os.path.join(PROJECT_ROOT, "docs/evidence/meta-orchestrator")
        os.makedirs(evidence_dir, exist_ok=True)

        matrix_path = os.path.join(evidence_dir, f"{ts}-domain-coverage-matrix.md")
        gap_path = os.path.join(evidence_dir, f"{ts}-gap-scan.md")
        brief_path = os.path.join(evidence_dir, f"{ts}-daily-autonomy-brief.md")

        with open(matrix_path, "w") as f:
            f.write(matrix_md)
        with open(gap_path, "w") as f:
            # Write gap scan list as markdown
            gap_lines = ["# Gap Scan Results", ""]
            for g in gaps:
                gap_lines.append(f"- **[{g['severity']}]** {g['description']} (Target: `{g['target']}`)")
            f.write("\n".join(gap_lines))
        with open(brief_path, "w") as f:
            f.write(brief_md)

        # Update domain registry records with evidence paths
        for d in self.registry.get_all_domains():
            self.registry.register_evidence(d["domain_id"], matrix_path)

        return {
            "metrics": metrics,
            "gaps": gaps,
            "decisions": decisions,
            "brief_md": brief_md,
            "evidence_paths": {
                "matrix": matrix_path,
                "gaps": gap_path,
                "brief": brief_path
            }
        }
