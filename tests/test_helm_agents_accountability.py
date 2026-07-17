"""Accountability view: only ledger dimensions; no fabricated agent continuity."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_pkg(tmp: Path, *, broken_chain: bool = False) -> Path:
    pkg = tmp / "HELM-SOAK-2H-TEST"
    daemon = pkg / "daemon"
    daemon.mkdir(parents=True)
    (pkg / "soak_config.json").write_text(json.dumps({
        "phase": "A", "seconds": 7200, "started_at": "2026-07-14T20:00:00Z",
        "tested_commit": "deadbeef", "scheduler_instance_id": "sched-test",
    }))
    env = [
        {
            "task_id": "SOAK-HASF-1", "factory": "HASF", "adapter": "LOCAL_OLLAMA",
            "worker_id": "worker-aaa", "scheduler_instance_id": "sched-test",
            "authority_decision_id": "AUTH-1", "authority_status": "ACTIVE",
            "authority_class": "AUTONOMOUS",
            "dispatch_digest": "d" * 32, "artifact_sha256": "a" * 32,
            "fencing_token": 1, "lease_id": "lease-1",
            "started_at": "2026-07-14T20:00:00Z", "completed_at": "2026-07-14T20:00:30Z",
            "cost_usd": 0.0, "cost_state": "OBSERVED", "out_chars": 1000, "in_chars": 100,
        },
        {
            "task_id": "SOAK-HASF-2", "factory": "HASF", "adapter": "LOCAL_OLLAMA",
            "worker_id": "worker-bbb", "scheduler_instance_id": "sched-test",
            "authority_decision_id": "AUTH-2", "authority_status": "ACTIVE",
            "authority_class": "AUTONOMOUS",
            "dispatch_digest": "e" * 32, "artifact_sha256": "b" * 32,
            "fencing_token": 2, "lease_id": "lease-2",
            "started_at": "2026-07-14T20:01:00Z", "completed_at": "2026-07-14T20:01:40Z",
            "cost_usd": 0.0, "cost_state": "OBSERVED", "out_chars": 800, "in_chars": 80,
        },
        {
            "task_id": "SOAK-HRF-1", "factory": "HRF", "adapter": "LOCAL_OLLAMA",
            "worker_id": "worker-ccc", "scheduler_instance_id": "sched-test",
            "authority_decision_id": "AUTH-3", "authority_status": "ACTIVE",
            "authority_class": "AUTONOMOUS",
            "dispatch_digest": "f" * 32, "artifact_sha256": "c" * 32,
            "fencing_token": 1, "lease_id": "lease-3",
            "started_at": "2026-07-14T20:00:05Z", "completed_at": "2026-07-14T20:00:20Z",
            "cost_usd": 0.0, "cost_state": "OBSERVED", "out_chars": 900, "in_chars": 90,
        },
    ]
    ver = [
        {"task_id": "SOAK-HASF-1", "factory": "HASF", "validator": "validate_hasf",
         "verdict": "PASS", "failed_checks": []},
        {"task_id": "SOAK-HASF-2", "factory": "HASF", "validator": "validate_hasf",
         "verdict": "FAIL", "failed_checks": [{"check": "references_subject_module"}]},
        {"task_id": "SOAK-HRF-1", "factory": "HRF", "validator": "validate_hrf",
         "verdict": "PASS", "failed_checks": []},
    ]
    (daemon / "result_envelopes.jsonl").write_text(
        "\n".join(json.dumps(r) for r in env) + "\n")
    (daemon / "verification_ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in ver) + "\n")
    # minimal lease ledger (unchained → CONTRADICTED if verify_chain fails closed)
    if broken_chain:
        (daemon / "task_lease_ledger.jsonl").write_text(
            json.dumps({"task_id": "SOAK-HASF-1", "status": "ACQUIRED", "prev_hash": "dead",
                        "entry_hash": "beef"}) + "\n")
    else:
        # no lease chain file → chain_state UNKNOWN, view still CONFIRMED_LIVE if ver total
        pass
    return pkg


def test_agents_matrix_names_failing_check(tmp_path, monkeypatch):
    pkg = _write_pkg(tmp_path)
    import backend.helm_live_api as api
    monkeypatch.setattr(api, "PKGS", tmp_path)
    monkeypatch.setattr(api, "_newest_soak_pkg", lambda: pkg)
    monkeypatch.setattr(api, "ROOT", tmp_path)
    # relative_to needs ROOT under pkg parent
    monkeypatch.setattr(api, "ROOT", tmp_path)
    c = TestClient(api.app)
    r = c.get("/api/v1/helm/agents")
    assert r.status_code == 200
    d = r.json()
    x = d.get("data") or d
    assert x["state"] in ("CONFIRMED_LIVE", "UNKNOWN", "CONTRADICTED")
    assert x["doctrine"]["no_named_agent_leaderboard"] is True
    assert x["adapter_count"] == 1
    assert "1 adapter" in (x.get("adapter_count_label") or "")
    assert x["cost_display"].startswith("$0.00")
    assert "OBSERVED" in x["cost_display"]
    hasf = next(m for m in x["matrix"] if m["factory"] == "HASF")
    assert hasf["fail"] == 1
    assert hasf["failing_checks"].get("references_subject_module") == 1
    # no empty adapter lanes
    assert all(a["runs"] > 0 for a in x["adapters"])
    # ephemeral workers counted, not ranked
    assert x["ephemeral_worker_executions"] == 3
    # custody includes auth decision
    assert any(c.get("authority_decision_id") for c in x["custody"])


def test_agents_unknown_without_package(tmp_path, monkeypatch):
    import backend.helm_live_api as api
    monkeypatch.setattr(api, "_newest_soak_pkg", lambda: None)
    c = TestClient(api.app)
    r = c.get("/api/v1/helm/agents")
    x = r.json().get("data") or r.json()
    assert x["state"] == "UNKNOWN"
