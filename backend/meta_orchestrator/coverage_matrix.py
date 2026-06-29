from typing import Dict, List, Any
from backend.meta_orchestrator.domain_registry import DomainRegistry

class CoverageMatrix:
    def __init__(self, registry: DomainRegistry):
        self.registry = registry

    def compute_metrics(self) -> Dict[str, Any]:
        domains = self.registry.get_all_domains()
        total = len(domains)
        owned = sum(1 for d in domains if d["owner_agent"] != "unassigned")
        score = (owned / total) * 100.0 if total > 0 else 100.0
        ownerless = [d["domain_id"] for d in domains if d["owner_agent"] == "unassigned"]
        
        return {
            "domain_coverage_score": round(score, 1),
            "total_domains": total,
            "owned_domains_count": owned,
            "ownerless_domains_count": len(ownerless),
            "ownerless_domain_ids": ownerless
        }

    def generate_matrix_markdown(self) -> str:
        domains = self.registry.get_all_domains()
        lines = [
            "# Domain Coverage Matrix",
            "",
            "| Domain ID | Name | Owner Agent | Maturity | Status | Risk Level | Revenue Relevance |",
            "|---|---|---|---|---|---|---|",
        ]
        for d in sorted(domains, key=lambda x: x["domain_id"]):
            lines.append(
                f"| `{d['domain_id']}` | {d['name']} | `{d['owner_agent']}` | {d['maturity_level']} | {d['status']} | {d['risk_level']} | {d['revenue_relevance']} |"
            )
        return "\n".join(lines)
