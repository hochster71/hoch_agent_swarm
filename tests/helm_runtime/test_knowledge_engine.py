"""Tests for the Knowledge Engine — governed retrieval (EDR-0004 v1).

Builder's own regression + negative tests proving the door is closed by
construction: retrieval is read-only and honest; the policy fails closed on
secrets; ingestion is governance-bound and emits an event. Grok (Auditor) owns
the authoritative adversarial pass.

Uses a temp corpus + temp event bus so the real runtime state is never touched.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

import pytest

from backend.helm_runtime import knowledge_engine as ke
from backend.helm_runtime import event_bus as eb


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    """A tiny governed corpus mirroring the real root layout, plus a temp bus."""
    root = tmp_path
    (root / "docs" / "helm" / "edr").mkdir(parents=True)
    (root / "docs" / "evidence").mkdir(parents=True)
    (root / "coordination" / "goal").mkdir(parents=True)

    (root / "docs" / "helm" / "HELM_CONSTITUTION_v1.0.md").write_text(
        "# HELM Constitution v1.0\nArticle II — truth is derived, never invented.\n",
        encoding="utf-8",
    )
    (root / "docs" / "helm" / "edr" / "EDR-0004-knowledge-engine.md").write_text(
        "# EDR-0004 — Knowledge Engine\nGoverned retrieval for cross-model neutrality.\n",
        encoding="utf-8",
    )
    (root / "docs" / "helm" / "edr" / "EDR-0001-runtime-bridge.md").write_text(
        "# EDR-0001 — Runtime Bridge\nThe role-based door.\n", encoding="utf-8"
    )
    (root / "docs" / "evidence" / "VERIFICATION_report.md").write_text(
        "# Verification\nBridge verified conformant.\n", encoding="utf-8"
    )
    # A secret-shaped file INSIDE a corpus root — policy must never surface it.
    (root / "docs" / "helm" / "provider_secret.md").write_text(
        "sk-live-DEADBEEF should never be retrievable\n", encoding="utf-8"
    )

    events = root / "helm_events.jsonl"
    # publish_event reads eb.EVENTS_PATH at call-time (path or EVENTS_PATH), so
    # patching the module global redirects writes to the temp bus. tail_events,
    # however, binds `path=EVENTS_PATH` as a def-time default (frozen module), so
    # the global patch never reaches it — it would read the REAL event log. Pin
    # its path to the same temp bus so assertions read the bus under test.
    monkeypatch.setattr(eb, "EVENTS_PATH", events, raising=True)
    monkeypatch.setattr(eb, "tail_events", functools.partial(eb.tail_events, path=events), raising=True)
    return root


# ---- Manifest: derived, provenanced, honest ----------------------------------

def test_manifest_indexes_governed_files_only(corpus):
    man = ke.build_manifest(root=corpus)
    paths = {d["path"] for d in man["documents"]}
    assert any(p.endswith("EDR-0004-knowledge-engine.md") for p in paths)
    assert any("CONSTITUTION" in p.upper() for p in paths)
    # Secret-shaped file is excluded by the policy, never indexed.
    assert not any("secret" in p.lower() for p in paths)
    # Every item carries provenance + freshness (EDR-0004 AC).
    for d in man["documents"]:
        assert "source_path" in d["provenance"]
        assert d["freshness"]["status"] in ("FRESH", "STALE", "UNKNOWN")


def test_kind_classification(corpus):
    man = ke.build_manifest(root=corpus)
    kinds = {d["path"]: d["kind"] for d in man["documents"]}
    con = next(p for p in kinds if "CONSTITUTION" in p.upper())
    edr = next(p for p in kinds if p.endswith("EDR-0004-knowledge-engine.md"))
    ev = next(p for p in kinds if "VERIFICATION" in p.upper())
    assert kinds[con] == "constitution"
    assert kinds[edr] == "edr"
    assert kinds[ev] == "evidence"


# ---- Retrieval: read-only, ranked, honest ------------------------------------

def test_retrieve_ranks_relevant_doc_first(corpus):
    res = ke.retrieve("knowledge engine governed retrieval", root=corpus)
    assert res["status"] == "OK"
    assert res["results"], "expected at least one governed hit"
    top = res["results"][0]
    assert top["path"].endswith("EDR-0004-knowledge-engine.md")
    assert top["provenance"]["source_path"] == top["path"]
    assert top["freshness"]["status"] in ("FRESH", "STALE")


def test_retrieve_kind_filter(corpus):
    res = ke.retrieve("bridge", kind="evidence", root=corpus)
    assert all(r["kind"] == "evidence" for r in res["results"])


def test_retrieve_absent_reports_unknown_not_fabricated(corpus):
    res = ke.retrieve("quantum tunneling flux capacitor xyzzy", root=corpus)
    assert res["status"] == "UNKNOWN"
    assert res["results"] == []


def test_retrieve_never_surfaces_secret(corpus):
    res = ke.retrieve("sk-live DEADBEEF secret", root=corpus, limit=50)
    for r in res["results"]:
        assert "secret" not in r["path"].lower()
        assert "sk-live-DEADBEEF" not in r["snippet"]


def test_retrieve_is_read_only_no_events(corpus):
    ke.retrieve("constitution", root=corpus)
    ke.build_manifest(root=corpus)
    ke.governed_load_constitution_and_edrs(root=corpus)
    # Read paths must never write to the event bus.
    assert eb.tail_events(n=10) == []


def test_retrieve_rejects_non_actor_role(corpus):
    for bad in ("truth", "runtime"):
        res = ke.retrieve("constitution", role=bad, root=corpus)
        assert res["status"] == "ROLE_REJECTED"
        assert res["results"] == []


# ---- One-call session load ---------------------------------------------------

def test_session_load_returns_constitution_and_edrs(corpus):
    res = ke.governed_load_constitution_and_edrs(root=corpus)
    assert res["status"] == "OK"
    assert len(res["constitution"]) == 1
    edr_paths = {e["path"] for e in res["edrs"]}
    assert any(p.endswith("EDR-0004-knowledge-engine.md") for p in edr_paths)
    assert any(p.endswith("EDR-0001-runtime-bridge.md") for p in edr_paths)


def test_freshness_marks_old_document_stale(corpus):
    res = ke.governed_load_constitution_and_edrs(root=corpus, stale_after_seconds=0)
    # With a zero staleness window everything on disk reads STALE, never faked.
    assert all(c["freshness"]["status"] == "STALE" for c in res["constitution"])


# ---- Governed ingestion: role/founder gates + event emission -----------------

def test_ingest_emits_event_with_provenance(corpus):
    r = ke.ingest("builder", "docs/helm/edr/EDR-0004-knowledge-engine.md", root=corpus)
    assert r["ok"] is True
    assert r["status"] == "INGESTED"
    assert r["kind"] == "edr"
    events = eb.tail_events(n=5)
    assert any(e.get("type") == "KNOWLEDGE_INGESTED" for e in events)
    evt = next(e for e in events if e.get("type") == "KNOWLEDGE_INGESTED")
    assert evt["payload"]["source_path"].endswith("EDR-0004-knowledge-engine.md")


def test_ingest_rejects_non_actor_role(corpus):
    r = ke.ingest("truth", "docs/helm/edr/EDR-0001-runtime-bridge.md", root=corpus)
    assert r["ok"] is False
    assert r["status"] == "ROLE_REJECTED"
    assert eb.tail_events(n=5) == []


def test_ingest_denies_secret_shaped_path(corpus):
    r = ke.ingest("builder", "docs/helm/provider_secret.md", root=corpus)
    assert r["ok"] is False
    assert r["status"] == "POLICY_DENIED"


def test_ingest_absent_source_reports_honestly(corpus):
    r = ke.ingest("builder", "docs/helm/edr/EDR-9999-missing.md", root=corpus)
    assert r["ok"] is False
    assert r["status"] == "SOURCE_ABSENT"


def test_constitution_ingestion_is_founder_gated(corpus):
    # Builder cannot ingest the Constitution at all.
    r = ke.ingest("builder", "docs/helm/HELM_CONSTITUTION_v1.0.md", root=corpus)
    assert r["ok"] is False
    assert r["status"] == "FOUNDER_GATE"
    # Founder without an authorization token is still refused.
    r2 = ke.ingest(
        "founder", "docs/helm/HELM_CONSTITUTION_v1.0.md", root=corpus,
        founder_token_present=False,
    )
    assert r2["ok"] is False
    assert r2["status"] == "FOUNDER_GATE"
    # Founder WITH token succeeds.
    r3 = ke.ingest(
        "founder", "docs/helm/HELM_CONSTITUTION_v1.0.md", root=corpus,
        founder_token_present=True,
    )
    assert r3["ok"] is True
    assert r3["kind"] == "constitution"


def test_ingest_role_not_permitted_kind(corpus):
    # Auditor may not ingest an EDR (builder-produced artifact).
    r = ke.ingest("auditor", "docs/helm/edr/EDR-0001-runtime-bridge.md", root=corpus)
    assert r["ok"] is False
    assert r["status"] == "ROLE_NOT_PERMITTED_KIND"
