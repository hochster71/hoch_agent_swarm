from backend.meta_orchestrator.domain_registry import DomainRegistry
from backend.meta_orchestrator.coverage_matrix import CoverageMatrix

def test_coverage_matrix_computes_correct_score():
    registry = DomainRegistry()
    matrix = CoverageMatrix(registry)
    
    # 4 domains are pre-assigned in registry initialization: Chief of Staff, Runtime Truth, Anti-Fake, QA/Test
    # Total domains = 43
    metrics = matrix.compute_metrics()
    assert metrics["total_domains"] == 43
    assert metrics["owned_domains_count"] == 4
    # 4 / 43 = 9.3%
    assert metrics["domain_coverage_score"] == 9.3
    assert metrics["ownerless_domains_count"] == 39
