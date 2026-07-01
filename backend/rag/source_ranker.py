import os
import yaml

class SourceRanker:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.sources_path = os.path.join(root_dir, "config/trusted_cyber_sources.yaml")

    def rank_sources(self, query: str) -> list:
        if not os.path.exists(self.sources_path):
            return []
            
        with open(self.sources_path, "r") as f:
            data = yaml.safe_load(f) or {}
            
        sources = data.get("trusted_cyber_sources", {}).get("sources", [])
        query_lower = query.lower()
        
        ranked = []
        for s in sources:
            name = s.get("name", "")
            url = s.get("url", "")
            confidence = s.get("confidence", 1.0)
            
            # Simple keyword matching relevance
            score = 0.1
            words = name.lower().split() + url.lower().split("/")
            for word in words:
                if len(word) > 2 and word in query_lower:
                    score += 0.3
                    
            ranked.append({
                "name": name,
                "url": url,
                "confidence": confidence,
                "relevance_score": round(min(score, 1.0), 2)
            })
            
        # Sort by relevance and then confidence
        return sorted(ranked, key=lambda x: (x["relevance_score"], x["confidence"]), reverse=True)
