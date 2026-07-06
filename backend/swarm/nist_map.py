"""NIST SP 800-53 Rev 5 arterial map — HOCH's prompts as the control circulatory system.

Maps every BRAIN gene domain to its NIST 800-53 Rev 5 control family (20 families) and computes,
per family, how much of the library covers it + the cyber-swarm's live posture. This is the data
behind the brain-arteries visual: each control family is an 'artery'; its strength = the genes
flowing through it; SI/RA carry the swarm's live detection posture.

Grounded: 20 families per NIST SP 800-53 Rev 5 (Rev 4 had 18; PT + SR added). Honest: a family with
zero mapped genes reads UNCOVERED — never fabricated as covered.
"""
import json
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "prompt_brain"

# The 20 NIST SP 800-53 Rev 5 control families.
FAMILIES = {
    "AC": "Access Control", "AT": "Awareness & Training", "AU": "Audit & Accountability",
    "CA": "Assessment, Authorization & Monitoring", "CM": "Configuration Management",
    "CP": "Contingency Planning", "IA": "Identification & Authentication", "IR": "Incident Response",
    "MA": "Maintenance", "MP": "Media Protection", "PE": "Physical & Environmental Protection",
    "PL": "Planning", "PM": "Program Management", "PS": "Personnel Security",
    "PT": "PII Processing & Transparency", "RA": "Risk Assessment",
    "SA": "System & Services Acquisition", "SC": "System & Communications Protection",
    "SI": "System & Information Integrity", "SR": "Supply Chain Risk Management",
}

# Map each BRAIN gene domain (task_class) -> the NIST families it feeds.
DOMAIN_TO_NIST = {
    "Cybersecurity": ["SC", "SI"], "DevSecOps": ["CM", "SA"], "Detection-Engineering": ["SI", "IR"],
    "Detection Engineering": ["SI", "IR"], "SAST": ["RA", "SA", "SI"], "DAST": ["RA", "SI"],
    "Vulnerability-Management": ["RA", "SI"], "Vulnerability Management": ["RA", "SI"],
    "Security-Architecture": ["SC", "IA", "AC"], "Security Architecture": ["SC", "IA", "AC"],
    "Cloud-Security": ["SC", "CM"], "Cloud Security": ["SC", "CM"],
    "Data-Security": ["MP", "PT", "IA"], "Data Security": ["MP", "PT", "IA"],
    "Incident-Response": ["IR"], "Incident Response": ["IR"],
    "Self-Healing": ["CP", "SI"], "Privacy": ["PT"], "Supply-Chain": ["SR"], "Supply Chain": ["SR"],
    "Governance": ["PM", "PL", "CA"], "Governance-Compliance": ["PM", "CA"],
    "Governance / Compliance": ["PM", "CA"], "SDLC-Governance": ["CM", "PL", "SA"],
    "SDLC Governance": ["CM", "PL", "SA"], "Audit": ["AU", "CA"], "QA": ["CA", "SA"],
    "Coding": ["SA"], "Software-Engineering": ["SA"], "Software Engineering": ["SA"],
    "Infrastructure-Hardware": ["PE", "MA"], "Infrastructure & Hardware": ["PE", "MA"],
    "Operations": ["MA", "CP"], "Legal-Compliance": ["CA", "PM"], "Legal / Compliance": ["CA", "PM"],
    "UX-Security": ["AC", "SI"], "UX Security": ["AC", "SI"], "AI-ML": ["SA", "SI"], "AI / ML": ["SA", "SI"],
    "AGI-Safety": ["PM", "RA"], "AGI & Safety": ["PM", "RA"], "Industry-Specialized": ["PM"],
    "Industry Specialized": ["PM"],
}


def build() -> Dict[str, Any]:
    gp = {}
    try:
        gp = json.loads((DATA / "gene_pool_m0.json").read_text())
    except Exception:
        pass
    sizes = gp.get("class_sizes", {})
    fam_genes = {k: 0 for k in FAMILIES}
    fam_domains = {k: set() for k in FAMILIES}
    for domain, n in sizes.items():
        for fam in DOMAIN_TO_NIST.get(domain, []):
            fam_genes[fam] += n
            fam_domains[fam].add(domain)

    swarm = {}
    try:
        swarm = json.loads((DATA / "cyber_swarm_state.json").read_text())
    except Exception:
        pass

    families = []
    for fam, name in FAMILIES.items():
        g = fam_genes[fam]
        entry = {"family": fam, "name": name, "genes": g, "covered": g > 0,
                 "domains": sorted(fam_domains[fam])}
        # SI + RA carry the live swarm detection posture (integrity / risk).
        if fam in ("SI", "RA") and swarm:
            entry["swarm_coverage"] = swarm.get("detection_coverage_pct")
            entry["swarm_verdict"] = swarm.get("verdict")
        families.append(entry)

    covered = sum(1 for f in families if f["covered"])
    total_genes = sum(fam_genes.values())
    out = {
        "schema": "nist-800-53-r5-arterial-map",
        "standard": "NIST SP 800-53 Rev 5 (20 control families; DoD RMF aligned)",
        "families_total": 20, "families_covered": covered,
        "coverage_pct": round(100.0 * covered / 20, 1),
        "mapped_gene_paths": total_genes,
        "families": sorted(families, key=lambda x: -x["genes"]),
    }
    (DATA).mkdir(parents=True, exist_ok=True)
    (DATA / "nist_map.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    m = build()
    print(f"NIST 800-53 Rev 5 arterial map: {m['families_covered']}/20 families covered "
          f"({m['coverage_pct']}%), {m['mapped_gene_paths']} gene→control paths")
    for f in m["families"][:8]:
        sw = f" · swarm {f.get('swarm_coverage')}%" if f.get("swarm_coverage") is not None else ""
        print(f"  {f['family']} {f['name'][:34]:34} genes={f['genes']:>3}{sw}")
    unc = [f['family'] for f in m['families'] if not f['covered']]
    print(f"  UNCOVERED families: {unc or 'none'}")
