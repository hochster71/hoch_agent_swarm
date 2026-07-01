from typing import Dict, List, Any

# Reference blueprints for files, business modules, and evidence chains that SHOULD exist
REFERENCE_MODELS = {
    "sdlc": [
        "pyproject.toml",
        "README.md",
        "tests/",
        "docs/"
    ],
    "ddlc": [
        "docs/evidence/runtime/",
        "docs/evidence/meta-orchestrator/"
    ],
    "business": [
        "docs/monetization/offers/ai-cyber-artifact-factory-one-pager.md",
        "docs/monetization/offers/ai-cyber-artifact-factory-pricing.md",
        "docs/monetization/offers/buyer-profile.md"
    ],
    "revenue": [
        "docs/monetization/outreach/outreach-draft.md",
        "docs/monetization/sample-package/sample-deck-outline.md"
    ],
    "risk": [
        "LICENSE",
        "docs/monetization/sample-package/public-safe-sanitizer-report.md"
    ]
}
