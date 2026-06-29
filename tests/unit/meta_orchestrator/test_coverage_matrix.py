from backend.meta_orchestrator.domain_registry import DomainRegistry
from backend.meta_orchestrator.coverage_matrix import CoverageMatrix

def test_coverage_matrix_computes_correct_score():
    registry = DomainRegistry()
    matrix = CoverageMatrix(registry)
    
    # All 43 domains are assigned by default
    metrics = matrix.compute_metrics()
    assert metrics["total_domains"] == 43
    assert metrics["owned_domains_count"] == 43
    assert metrics["domain_coverage_score"] == 100.0
    assert metrics["ownerless_domains_count"] == 0
