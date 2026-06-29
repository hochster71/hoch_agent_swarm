# revenue_offer_packager.py
from pathlib import Path

class RevenueOfferPackager:
    def __init__(self):
        pass

    def get_offers(self) -> list[dict]:
        return [
            {
                "offer_id": "OFFER-001",
                "title": "AI Cyber Artifact Factory",
                "description": "Enterprise-grade local-first automated cybersecurity artifact and RMF audit evidence generation engine.",
                "components": [
                    "Citations & sources indexing appendix generator",
                    "Automated DOCX / PPTX / PDF exports",
                    "Hoch-branded visual dashboard template bundles",
                    "SQLite audit log trail & cryptographic signers"
                ],
                "pricing": {
                    "tier_1_local": "$4,500/year self-hosted license",
                    "tier_2_support": "$12,000/year with DevSecOps swarm setup support"
                },
                "status": "LAUNCH_READY"
            },
            {
                "offer_id": "OFFER-002",
                "title": "Secure Local AI Agent Swarm Setup",
                "description": "Turnkey local-first model router and agent execution mesh, utilizing Ollama/Llama3 for zero-cloud data leaks.",
                "components": [
                    "Local capability routing gateway",
                    "Automated preflight checks & ATO validation scripts",
                    "24/7 self-healing watchdogs & reliability pond",
                    "Dockerized secure execution sandboxing config"
                ],
                "pricing": {
                    "flat_setup": "$8,500 one-time integration engineering fee",
                    "recurring_maintenance": "$1,500/month continuous audit updates"
                },
                "status": "LAUNCH_READY"
            }
        ]
