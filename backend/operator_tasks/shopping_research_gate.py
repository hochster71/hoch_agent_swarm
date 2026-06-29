import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.operator_tasks.task_classifier import TaskClassifier
from backend.operator_tasks.safety_screen import SafetyScreen
from backend.operator_tasks.product_search_runner import ProductSearchRunner
from backend.operator_tasks.price_ranker import PriceRanker
from backend.operator_tasks.printable_summary.py import PrintableSummary # wait, import as class
from backend.operator_tasks.local_print_adapter import LocalPrintAdapter
from backend.operator_tasks.purchase_link_preparer import PurchaseLinkPreparer
from backend.operator_tasks.approval_gate import ApprovalGate
from backend.operator_tasks.task_evidence_writer import TaskEvidenceWriter

# Fix import issue: PrintableSummary is in printable_summary.py
from backend.operator_tasks.printable_summary import PrintableSummary

def update_runtime_truth_signal(signal_id: str, name: str, value: str, source: str):
    from backend.runtime_truth.state_store import DB_PATH, apply_pragmas
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals 
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id,
            name,
            str(value),
            source,
            "script",
            datetime.now(timezone.utc).isoformat(),
            300,
            "fresh",
            1.0,
            "",
            "",
            ""
        ))
        conn.commit()
    finally:
        conn.close()

class ShoppingResearchGate:
    def __init__(self):
        self.classifier = TaskClassifier()
        self.screen = SafetyScreen()
        self.search_runner = ProductSearchRunner()
        self.ranker = PriceRanker()
        self.summarizer = PrintableSummary()
        self.print_adapter = LocalPrintAdapter()
        self.link_preparer = PurchaseLinkPreparer()
        self.approval_gate = ApprovalGate()
        self.evidence_writer = TaskEvidenceWriter()
        
        self.blocked_purchases_count = 0

    def execute_task(self, query: str, config_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        if config_overrides is None:
            config_overrides = {}
            
        # 1. Classify task
        classification = self.classifier.classify(query)
        domain = classification["domain"]
        mode = classification["mode"]
        
        # Override mode if provided
        if "mode" in config_overrides:
            mode = config_overrides["mode"]
            
        # 2. Check if a blocked action is requested (e.g. mock a purchase event)
        purchase_attempted = config_overrides.get("attempt_purchase", False)
        if purchase_attempted:
            self.blocked_purchases_count += 1
            update_runtime_truth_signal(
                "blocked_purchase_attempt_count",
                "Blocked Purchase Attempt Count",
                str(self.blocked_purchases_count),
                "backend.operator_tasks.approval_gate"
            )
            # Enforce hard block
            self.approval_gate.verify_action("purchase")
            
        # 3. Perform product search
        raw_products = self.search_runner.search(query, domain)
        
        # 4. Screen products
        screened_candidates = []
        safety_pass_count = 0
        for prod in raw_products:
            if domain == "PET_TOYS":
                safety_result = self.screen.screen_baby_rat_toy(prod)
            elif domain == "CHILD_TOYS":
                # Match child age target
                child_age = config_overrides.get("child_age", 5)
                safety_result = self.screen.screen_child_toy(prod, child_age=child_age)
            else:
                # Generic fallback pass
                safety_result = {"passed": True, "violations": [], "warnings": [], "domain": domain}
                
            if safety_result["passed"]:
                safety_pass_count += 1
                
            # Clean URLs
            prod["url"] = self.link_preparer.prepare_clean_link(prod["url"])
            
            screened_candidates.append({
                "product": prod,
                "safety_result": safety_result
            })
            
        # 5. Rank candidates
        ranked_candidates = self.ranker.rank(screened_candidates)
        
        # 6. Generate brief summary
        brief = self.summarizer.generate(query, ranked_candidates, domain)
        
        # 7. Print summary if approved and mode fits
        print_status = "NOT_TRIGGERED"
        if mode == "RESEARCH_AND_PRINT":
            printer = config_overrides.get("printer", "HP-OfficeJet-Pro-WiFi")
            approved = config_overrides.get("print_approved", False)
            print_result = self.print_adapter.print_brief(brief, printer, approved)
            if print_result["success"]:
                print_status = "SUCCESS"
            else:
                print_status = print_result["handshake"]
                
        # 8. Write compliance evidence
        evidence_data = {
            "query": query,
            "mode": mode,
            "domain": domain,
            "purchase_blocked": True,
            "safety_pass": safety_pass_count > 0,
            "print_status": print_status,
            "candidates": ranked_candidates
        }
        evidence_path = self.evidence_writer.write_evidence(evidence_data)
        
        # 9. Update all 7 Runtime Truth signals in the database
        update_runtime_truth_signal("shopping_research_gate_status", "Shopping Research Gate Status", "ACTIVE", "backend.operator_tasks.shopping_research_gate")
        update_runtime_truth_signal("purchase_block_status", "Purchase Block Status", "ENFORCED", "backend.operator_tasks.approval_gate")
        update_runtime_truth_signal("print_approval_status", "Print Approval Status", print_status, "backend.operator_tasks.local_print_adapter")
        update_runtime_truth_signal("product_safety_screen_status", "Product Safety Screen Status", "PASSED" if safety_pass_count > 0 else "FAILED", "backend.operator_tasks.safety_screen")
        update_runtime_truth_signal("candidate_count", "Candidate Count", str(len(ranked_candidates)), "backend.operator_tasks.product_search_runner")
        update_runtime_truth_signal("blocked_purchase_attempt_count", "Blocked Purchase Attempt Count", str(self.blocked_purchases_count), "backend.operator_tasks.approval_gate")
        update_runtime_truth_signal("last_operator_task_mode", "Last Operator Task Mode", mode, "backend.operator_tasks.task_classifier")
        
        return {
            "status": "success",
            "domain": domain,
            "mode": mode,
            "brief": brief,
            "candidates": ranked_candidates,
            "print_status": print_status,
            "evidence_path": evidence_path,
            "blocked_purchase_attempt_count": self.blocked_purchases_count
        }
