from typing import Dict, List, Any

class DailyAutonomyBrief:
    def __init__(self):
        pass

    def compile_brief(self, metrics: Dict[str, Any], gaps: List[Dict[str, Any]], decisions: List[Dict[str, Any]]) -> str:
        lines = [
            "# Daily Autonomy Brief",
            "",
            "## 1. System Health Metrics",
            f"- **Domain Coverage Score**: {metrics.get('domain_coverage_score', 0)}%",
            f"- **Ownerless Domain Count**: {metrics.get('ownerless_domains_count', 0)}",
            f"- **Critical Gap Count**: {len([g for g in gaps if g['severity'] == 'CRITICAL'])}",
            f"- **Michael Orchestration Load Score**: {metrics.get('michael_orchestration_load', 0.0)}",
            "",
            "## 2. Discovered Gaps",
        ]
        if not gaps:
            lines.append("- No gaps detected today.")
        for g in gaps:
            lines.append(f"- **[{g['severity']}]** {g['description']} (Target: `{g['target']}`)")
            
        lines.append("")
        lines.append("## 3. Pending Decisions in Queue")
        if not decisions:
            lines.append("- No decisions pending.")
        for d in decisions:
            lines.append(f"- **[{d['severity']}]** {d['title']}: {d['description']}")
            
        return "\n".join(lines)
