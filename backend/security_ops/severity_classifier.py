from typing import Dict, Any

class SeverityClassifier:
    def __init__(self):
        pass

    def classify_finding(self, finding_id: str, cvss_score: float) -> Dict[str, Any]:
        severity = "LOW"
        blocks_release = False

        if cvss_score >= 9.0:
            severity = "CRITICAL"
            blocks_release = True
        elif cvss_score >= 7.0:
            severity = "HIGH"
            blocks_release = True
        elif cvss_score >= 4.0:
            severity = "MEDIUM"
            blocks_release = False
            
        return {
            "finding_id": finding_id,
            "cvss_score": cvss_score,
            "severity": severity,
            "blocks_release": blocks_release
        }
