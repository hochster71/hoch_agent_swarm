import os
from typing import List, Dict, Any
from backend.gap_discovery.lifecycle_gap_scanner import LifecycleGapScanner
from backend.gap_discovery.business_gap_scanner import BusinessGapScanner
from backend.gap_discovery.app_gap_scanner import AppGapScanner
from backend.gap_discovery.revenue_gap_scanner import RevenueGapScanner
from backend.gap_discovery.risk_gap_scanner import RiskGapScanner
from backend.gap_discovery.evidence_gap_scanner import EvidenceGapScanner

class OmissionDetector:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.scanners = [
            LifecycleGapScanner(project_root),
            BusinessGapScanner(project_root),
            AppGapScanner(project_root),
            RevenueGapScanner(project_root),
            RiskGapScanner(project_root),
            EvidenceGapScanner(project_root)
        ]

    def run_all_scans(self) -> List[Dict[str, Any]]:
        all_gaps = []
        for scanner in self.scanners:
            try:
                all_gaps.extend(scanner.scan())
            except Exception as e:
                all_gaps.append({
                    "category": "system",
                    "target": "scanner_loop",
                    "description": f"Scanner failed: {str(e)}",
                    "severity": "MEDIUM"
                })
        return all_gaps
