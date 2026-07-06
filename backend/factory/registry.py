"""HOCH Factory registry — the domain-aware contract.

One Governor (HAS), one Mind (BRAIN), many Makers (Factories). Each Factory declares its domain
namespace, its BRAIN state paths, its rubric + scorer, and its publish gates. The domain-agnostic
convergence engine (harvest, splits, gap_analysis, gene_expansion, improve_loop, convergence,
research_meta) operates on whatever paths + rubric a Factory hands it — so adding a Factory is
DECLARING one of these, not rewriting the engine.

Backward compatibility: the SOFTWARE factory keeps the existing FLAT data/prompt_brain paths so the
running brain is untouched. New domains (music, ...) live in data/prompt_brain/<domain>/.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
BRAIN = ROOT / "data" / "prompt_brain"
CONFIG = ROOT / "config"


@dataclass
class Factory:
    domain: str                 # state namespace, e.g. "software" | "music"
    code: str                   # HASF | HMF | ...
    title: str
    gene_pool: Path
    champion_registry: Path
    convergence_status: Path
    rubric: Path
    scorer_module: str          # dotted path to a module exposing score_prompt(text, rubric_path)
    publish_tier: str = "T3"    # publishing/monetizing always requires operator approval
    gates: List[str] = field(default_factory=list)

    def scorer(self) -> Callable:
        """Lazily import the domain scorer's score_prompt (avoids import cycles at module load)."""
        import importlib
        return importlib.import_module(self.scorer_module).score_prompt


# --- The registry ------------------------------------------------------------------------------
# SOFTWARE keeps the historical flat layout (unbroken). MUSIC is the first subfoldered domain.
_FACTORIES = {
    "software": Factory(
        domain="software", code="HASF", title="Hoch Application Software Factory",
        gene_pool=BRAIN / "gene_pool_m0.json",
        champion_registry=BRAIN / "champion_registry.json",
        convergence_status=BRAIN / "convergence_status.json",
        rubric=CONFIG / "prompt_score_rubric.yaml",
        scorer_module="backend.brain_convergence.scorer",
        gates=["pytest", "audit_stack", "runtime_truth", "T3_deploy_operator_approval"],
    ),
    "music": Factory(
        domain="music", code="HMF", title="Hoch Music Factory",
        gene_pool=BRAIN / "music" / "gene_pool.json",
        champion_registry=BRAIN / "music" / "champion_registry.json",
        convergence_status=BRAIN / "music" / "convergence_status.json",
        rubric=CONFIG / "music_score_rubric.yaml",
        scorer_module="backend.brain_convergence.music_scorer",
        gates=["originality_check", "licensing_clearance", "audio_quality_judge",
               "T3_publish_operator_approval"],
    ),
    "research": Factory(
        domain="research", code="HRF", title="Hoch AI Research Factory",
        gene_pool=BRAIN / "research" / "gene_pool.json",
        champion_registry=BRAIN / "research" / "champion_registry.json",
        convergence_status=BRAIN / "research" / "convergence_status.json",
        rubric=CONFIG / "research_score_rubric.yaml",
        scorer_module="backend.brain_convergence.research_scorer",
        # citation_verification is the anti-hallucination gate: every claim must resolve to a real
        # source (PubMed/bioRxiv/ClinicalTrials/ChEMBL) before a finding is accepted or published.
        gates=["citation_verification", "no_fabricated_results", "reproducibility_check",
               "ethics_dual_use_review", "T3_publish_operator_approval"],
    ),
}


def get_factory(domain: str) -> Optional[Factory]:
    return _FACTORIES.get(domain)


def list_factories() -> List[Factory]:
    return list(_FACTORIES.values())


def ensure_domain_dirs(domain: str) -> None:
    """Create the BRAIN state folder for a domain if missing (no-op for flat software domain)."""
    f = _FACTORIES.get(domain)
    if f:
        f.gene_pool.parent.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    for f in list_factories():
        exists = "✓" if f.gene_pool.exists() else "—"
        print(f"[{exists}] {f.code:5s} {f.domain:9s} | rubric={f.rubric.name} "
              f"| scorer={f.scorer_module.split('.')[-1]} | gates={len(f.gates)}")
