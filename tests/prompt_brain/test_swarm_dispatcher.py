import json
from pathlib import Path
from unittest import mock
from backend.brain_convergence import swarm_dispatcher as sd


def test_scan_docs_for_tasks(tmp_path):
    docs_dir = tmp_path / "docs" / "prompt_brain"
    docs_dir.mkdir(parents=True)
    md_file = docs_dir / "test_scope.md"
    md_file.write_text("This paid pilot has **Nessus Vulnerability Triage** and **Other Task Review**.")
    
    found = sd.scan_docs_for_tasks(tmp_path)
    assert len(found) == 2
    tasks = [f["task_class"] for f in found]
    assert "Nessus Vulnerability Triage" in tasks
    assert "Other Task Review" in tasks


def test_scan_logs_for_tasks(tmp_path):
    log_file = tmp_path / "runtime_executions.jsonl"
    log_file.write_text('{"task": "New Audit Task"}\n{"domain": "Some Governance Check"}')
    
    found = sd.scan_logs_for_tasks(log_file)
    assert len(found) == 2
    tasks = [f["task_class"] for f in found]
    assert "New Audit Task" in tasks
    assert "Some Governance Check" in tasks


def test_dispatcher_seeding(tmp_path):
    DATA = tmp_path / "data" / "prompt_brain"
    DATA.mkdir(parents=True)
    
    gene_pool_path = DATA / "gene_pool_m0.json"
    gene_pool_path.write_text(json.dumps({
        "schema": "brain-convergence-gene-pool-m0",
        "count": 0,
        "task_classes": 0,
        "class_sizes": {},
        "genes": {}
    }))

    docs_dir = tmp_path / "docs" / "prompt_brain"
    docs_dir.mkdir(parents=True)
    md_file = docs_dir / "test_scope.md"
    md_file.write_text("We need **DISA STIG Checklist Review**.")

    BACKEND = {"kind": "ollama", "base": "http://x", "model": "llama3"}

    with mock.patch.object(sd, "detect_local_backend", return_value=BACKEND), \
         mock.patch.object(sd, "_ollama_generate", return_value="ROLE: STIG auditor. SCOPE: STIG checks. EVIDENCE: plist. ANTI-FAKE-GREEN: check. ROLLBACK: abort. OUTPUT: report."):

        # Directly test core logic of run by mocking the target file paths
        sd.scan_docs_for_tasks = lambda root: [{"task_class": "DISA STIG Checklist Review", "source": "docs/test_scope.md"}]
        sd.scan_logs_for_tasks = lambda p: []
        
        sd.run(tmp_path)
        
        assert gene_pool_path.exists()
        pool = json.loads(gene_pool_path.read_text())
        assert pool["count"] == 1
        assert "DISA STIG Checklist Review" in pool["class_sizes"]
        
        # Check prompt seed
        gene = list(pool["genes"].values())[0]
        assert gene["task_class"] == "DISA STIG Checklist Review"
        assert "ROLE: STIG auditor." in gene["prompt"]
