from typing import List, Dict, Any

class AgentRoleRecommender:
    def recommend(self, ownerless_domains: List[str]) -> List[Dict[str, Any]]:
        recommendations = []
        for domain_id in ownerless_domains:
            agent_name = domain_id.replace("_", " ").title() + " Specialist Agent"
            recommendations.append({
                "domain_id": domain_id,
                "recommended_role": agent_name,
                "goal": f"Take full accountable ownership of the `{domain_id}` domain.",
                "backstory": f"You are a specialized agent designed to manage compliance, charters, status, and risks for the `{domain_id}` domain."
            })
        return recommendations
