class CitationEngine:
    def generate_citations(self, ranked_sources: list) -> list:
        citations = []
        for index, source in enumerate(ranked_sources):
            if source["relevance_score"] > 0.1:
                citations.append({
                    "ref_id": f"REF-{index + 1}",
                    "name": source["name"],
                    "url": source["url"],
                    "formatted": f"[{index + 1}] {source['name']} ({source['url']})"
                })
        return citations
