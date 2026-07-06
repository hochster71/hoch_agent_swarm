#!/usr/bin/env python3
"""Seed the HRF research gene pool with honest, rigorous starter agendas (labeled SEED).

Each gene is a research *agenda/protocol* (testable hypothesis, evidence standard, method, required
verifiable citations, kill criteria, moonshot framing) across humanity's grand-challenge domains —
the themes of the Moonshots podcast (longevity, AI, energy, space, neuro, climate, synbio, materials).
These are agendas, NOT findings: no result is asserted. task_class = grand-challenge domain, so the
same gap-analysis that finds thin software classes finds thin research domains. Deterministic.
"""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prompt_brain" / "research" / "gene_pool.json"

SEEDS = [
    ("Longevity", "Senolytic Combination vs Frailty",
     "Moonshot: extend healthy human lifespan (grand challenge). Testable hypothesis: a defined "
     "senolytic combination reduces a validated frailty index in aged cohorts vs placebo. Evidence "
     "standard: pre-registered endpoint (frailty index delta at 6 months), effect size + confidence "
     "interval; confirm/refute thresholds stated. Method: randomized controlled design, controls, "
     "sample size powered, protocol reproducible with open data. Literature grounding: cite prior "
     "senolytic trials via PubMed/bioRxiv DOIs — claims must cite verifiable primary sources, no "
     "assertions. Kill criteria: reject if no dose-response or safety signal. Ethics: IRB, informed "
     "consent, dual-use reviewed. Impact: healthspan for aging populations."),
    ("Longevity", "Epigenetic Clock Reversal Readout",
     "Moonshot: reverse biological age markers. Hypothesis: a partial-reprogramming protocol lowers "
     "a validated epigenetic clock without dedifferentiation. Evidence standard: clock delta with "
     "confidence interval, tumor-safety endpoint. Method: controlled in-vitro design, reproducible, "
     "open code. Literature: cite reprogramming papers (PubMed DOIs), verifiable only. Kill criteria: "
     "abort on oncogenic signal. Ethics/biosafety named. Impact: age-reversal therapeutics."),
    ("AI Safety", "Scalable Oversight of Superhuman Judges",
     "Moonshot: trustworthy oversight of models stronger than their evaluators (grand challenge). "
     "Testable hypothesis: debate-based scalable oversight raises judge accuracy on tasks the judge "
     "cannot directly verify vs baseline. Evidence standard: held-out accuracy delta, adversarial "
     "seeded-deception catch rate; confirm/refute stated. Method: controlled protocol, ablations, "
     "reproducible with open code. Literature grounding: cite alignment papers (arXiv/DOIs) — "
     "verifiable citations only, no fabricated references. Kill criteria: reject if judges are gamed "
     "by keyword stuffing. Ethics: dual-use, release review. Impact: safe advanced AI."),
    ("Fusion Energy", "High-Field Confinement Scaling Test",
     "Moonshot: net-energy fusion (abundance/energy grand challenge). Hypothesis: energy confinement "
     "time scales with field strength above a predicted threshold in a high-field configuration. "
     "Evidence standard: measured confinement vs predicted, error bars, success threshold. Method: "
     "instrumented experimental campaign, controls, reproducible data release. Literature: cite prior "
     "tokamak/stellarator results (verifiable DOIs). Kill criteria: stop if disruptions exceed limit. "
     "Safety: radiological review. Impact: clean baseload energy."),
    ("Space", "In-Situ Regolith Oxygen Yield",
     "Moonshot: off-world resource abundance. Hypothesis: a molten-regolith electrolysis process "
     "yields oxygen above a target rate from a lunar-simulant feedstock. Evidence standard: measured "
     "O2 yield vs target, energy-per-kg endpoint. Method: controlled bench protocol, reproducible, "
     "materials specified. Literature: cite ISRU studies (verifiable references). Kill criteria: "
     "reject below energy-efficiency floor. Safety named. Impact: sustainable off-world presence."),
    ("Neurotech", "Noninvasive BCI Decoding Fidelity",
     "Moonshot: high-bandwidth brain-computer interface. Hypothesis: a decoding model raises "
     "noninvasive imagined-speech accuracy above a stated baseline. Evidence standard: held-out "
     "decoding accuracy + confidence, chance-corrected. Method: preregistered protocol, cross-subject "
     "controls, open code. Literature: cite BCI papers (PubMed DOIs), verifiable only. Kill criteria: "
     "reject if not above chance cross-subject. Ethics: consent, neural-data privacy. Impact: "
     "communication for locked-in patients."),
    ("Climate", "Enhanced Weathering CO2 Drawdown",
     "Moonshot: gigaton carbon removal (grand challenge). Hypothesis: basalt enhanced weathering "
     "removes CO2 above a measured rate per hectare vs control plots. Evidence standard: net CDR with "
     "uncertainty, MRV endpoint. Method: field controls, reproducible, open data. Literature: cite "
     "weathering studies (DOIs). Kill criteria: reject if net-negative after energy accounting. "
     "Ethics/eco-safety. Impact: durable carbon removal."),
    ("Synthetic Biology", "Nitrogen-Fixing Cereal Symbiosis",
     "Moonshot: end synthetic-fertilizer dependence. Hypothesis: an engineered associative symbiosis "
     "raises fixed-nitrogen uptake in a cereal above baseline. Evidence standard: N-uptake delta, "
     "yield endpoint, containment metric. Method: controlled greenhouse protocol, reproducible. "
     "Literature: cite diazotroph work (verifiable DOIs). Kill criteria: reject on horizontal-gene "
     "escape. Biosafety/dual-use reviewed. Impact: food abundance, emissions cut."),
]


def _hash(t: str) -> str:
    return hashlib.sha256(t.strip().encode()).hexdigest()


def build():
    genes, sizes = {}, {}
    for domain, title, agenda in SEEDS:
        h = _hash(agenda)
        gid = f"seed-{domain[:4].lower().replace(' ', '')}-{h[:10]}"
        genes[gid] = {"gene_id": gid, "task_class": domain, "title": title,
                      "prompt": agenda, "content_hash": h, "state": "SEED",
                      "source": "HUMAN_SEED", "domain": "research"}
        sizes[domain] = sizes.get(domain, 0) + 1
    pool = {"schema": "brain-convergence-gene-pool-m0", "domain": "research",
            "count": len(genes), "task_classes": len(sizes),
            "class_sizes": dict(sorted(sizes.items(), key=lambda x: -x[1])), "genes": genes}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pool, indent=2), encoding="utf-8")
    print(f"seeded {len(genes)} research agendas across {len(sizes)} grand-challenge domains -> {OUT}")


if __name__ == "__main__":
    build()
