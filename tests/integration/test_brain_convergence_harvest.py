import json
import tempfile
from pathlib import Path

from backend.brain_convergence.harvest import harvest, normalize_gene, write_gene_pool


def _lib(recs):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(recs, f)
    f.close()
    return f.name


def test_normalize_gene_flattens_outputs_and_hashes():
    g = normalize_gene({"id": "x1", "category": "Cyber", "title": "T",
                        "prompt": "do the thing", "outputs": ["a", "b"]})
    assert g["task_class"] == "Cyber"
    assert g["outputs"] == "a, b"
    assert len(g["content_hash"]) == 64


def test_harvest_keys_by_task_class():
    lib = _lib([
        {"id": "1", "category": "Cyber", "title": "A", "prompt": "p1"},
        {"id": "2", "category": "Cyber", "title": "B", "prompt": "p2"},
        {"id": "3", "category": "AI", "title": "C", "prompt": "p3"},
    ])
    r = harvest(lib)
    assert r["count"] == 3
    assert r["task_classes"] == 2
    assert len(r["by_class"]["Cyber"]) == 2


def test_harvest_collapses_exact_content_duplicates():
    lib = _lib([
        {"id": "1", "category": "Cyber", "title": "A", "prompt": "same"},
        {"id": "2", "category": "Cyber", "title": "B", "prompt": "same"},  # dup content
    ])
    r = harvest(lib)
    assert r["count"] == 1
    assert r["collapsed"] == 1


def test_harvest_applies_capability_aliases():
    lib = _lib([
        {"id": "keep", "category": "Cyber", "title": "A", "prompt": "p1"},
        {"id": "drop", "category": "Cyber", "title": "B", "prompt": "p2"},
    ])
    af = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"drop": "keep"}, af); af.close()
    r = harvest(lib, aliases_path=af.name)
    assert r["count"] == 1
    assert "keep" in r["genes"] and "drop" not in r["genes"]
    assert r["collapsed"] == 1


def test_harvest_is_deterministic():
    lib = _lib([{"id": "1", "category": "X", "title": "A", "prompt": "p"}])
    assert harvest(lib)["genes"] == harvest(lib)["genes"]


def test_write_gene_pool_roundtrips():
    lib = _lib([{"id": "1", "category": "X", "title": "A", "prompt": "p"}])
    r = harvest(lib)
    out = tempfile.mktemp(suffix=".json")
    write_gene_pool(r, out)
    d = json.loads(Path(out).read_text())
    assert d["count"] == 1 and d["schema"] == "brain-convergence-gene-pool-m0"
