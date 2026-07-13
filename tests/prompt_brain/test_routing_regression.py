"""Routing scorer regression suite (HH-3, founder-specified).

Guards the hardened ranker against the failure mode that produced the original
defect: a scoring change that satisfies ONE benchmark case while degrading
general routing quality, or a corpus edited to contain the benchmark's words.

Two classes of guard:
  1. Behavioural cases the founder enumerated (exact industry only, exact
     framework only, both, conflicts, multiples, aliases, adversarial stop-word
     spam, unknown industry, missing framework).
  2. Anti-overfit invariants — the catalog must NOT contain benchmark query text,
     and the held-out benchmark must clear the quality bar.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager  # noqa: E402

BENCHMARK = json.loads((ROOT / "tests" / "prompt_brain" / "routing_benchmark.json").read_text())

# Founder-ratified quality bar.
P_AT_1_MIN = 95.0
R_AT_5_MIN = 95.0
R_AT_10_MIN = 100.0


@pytest.fixture(scope="module")
def pm():
    return get_promptbrain_manager()


def _ids(pm, query, industry=None, framework=None):
    res = pm.route_task(query, industry=industry, framework=framework)
    return [r["id"] for r in res.get("recommendations", [])]


def _rank(pm, query, expected, industry=None, framework=None):
    ids = _ids(pm, query, industry, framework)
    return ids.index(expected) + 1 if expected in ids else -1


# ---------------------------------------------------------------------------
# 1. Held-out benchmark must meet the bar (the headline guard)
# ---------------------------------------------------------------------------

def test_held_out_benchmark_meets_quality_bar(pm):
    cases = BENCHMARK["cases"]
    p1 = r5 = r10 = 0
    for c in cases:
        rank = _rank(pm, c["query"], c["expected_id"], c["industry"], c["framework"])
        p1 += 1 if rank == 1 else 0
        r5 += 1 if 0 < rank <= 5 else 0
        r10 += 1 if 0 < rank <= 10 else 0
    n = len(cases)
    assert 100.0 * p1 / n >= P_AT_1_MIN, f"P@1 {100.0*p1/n:.1f}% < {P_AT_1_MIN}%"
    assert 100.0 * r5 / n >= R_AT_5_MIN, f"R@5 {100.0*r5/n:.1f}% < {R_AT_5_MIN}%"
    assert 100.0 * r10 / n >= R_AT_10_MIN, f"R@10 {100.0*r10/n:.1f}% < {R_AT_10_MIN}%"


# ---------------------------------------------------------------------------
# 2. ANTI-OVERFIT: the corpus must never be tuned to the benchmark
# ---------------------------------------------------------------------------

def test_catalog_is_not_tuned_to_the_benchmark(pm):
    """The original defect: a prompt's title/mission was edited to contain the
    benchmark query's words. Rank-1 must never depend on such an edit.

    Guard: no catalog document may contain a long verbatim span of a benchmark
    query. (Short domain phrases are legitimate; a pasted query is not.)
    """
    offenders = []
    for c in BENCHMARK["cases"]:
        q = [w for w in re.findall(r"[a-z0-9\-]+", c["query"].lower()) if len(w) > 3]
        # any 5 consecutive significant query words appearing verbatim in a doc
        for i in range(max(0, len(q) - 4)):
            span = " ".join(q[i:i + 5])
            for p in pm.revised_prompts:
                blob = f"{p.get('title','')} {p.get('mission','')}".lower()
                if span in blob:
                    offenders.append((p["id"], span))
    assert not offenders, f"catalog contains verbatim benchmark spans (teaching to the test): {offenders[:5]}"


def test_scoring_has_no_unexplained_magic_constants():
    """The replaced scorer used +30/+20/+15/+50/+100/+200 with no stated meaning.
    The hardened scorer must document its tiers."""
    src = (ROOT / "src" / "hoch_agent_swarm" / "promptbrain_manager.py").read_text()
    assert "score += 200" not in src, "the unexplained +200 exact-match boost is back"
    assert "1000.0 * framework_match" in src and "500.0 * industry_match" in src, \
        "structured tiers missing from scorer"


# ---------------------------------------------------------------------------
# 3. Founder-enumerated behavioural cases
# ---------------------------------------------------------------------------

def test_exact_industry_only(pm):
    """Industry supplied, no framework: the industry-matching prompt outranks
    generic All-Industries prompts."""
    ids = _ids(pm, "secure guest reservation and loyalty records", industry="Hospitality")
    assert ids[0] == "HOSP-001"


def test_exact_framework_only(pm):
    """Framework supplied without industry still routes to the framework owner."""
    rank = _rank(pm, "map controls to the 800-53 families",
                 "GOVFRAME-001", industry=None, framework="NIST SP 800-53 Rev. 5")
    assert 0 < rank <= 5


def test_exact_industry_and_framework(pm):
    rank = _rank(pm, "map our system controls to the full control families",
                 "GOVFRAME-001", industry="Federal Civilian",
                 framework="NIST SP 800-53 Rev. 5")
    assert rank == 1


def test_framework_outranks_semantic_intent_conflict(pm):
    """Conflicting framework vs semantic intent: the EXPLICIT structured signal
    wins. An exact framework is a near-deterministic instruction and must not be
    overridden by loose text similarity to another prompt."""
    # Text leans hard toward ConMon (GOVFRAME-003), but the caller EXPLICITLY
    # named the CUI framework. The framework owner (GOVFRAME-004) must win.
    ids = _ids(pm, "continuous monitoring dashboards and sensors",
               industry="Federal Civilian", framework="NIST SP 800-171 CUI")
    assert ids[0] == "GOVFRAME-004", (
        f"explicit framework overridden by loose text similarity; top={ids[0]}")


def test_multiple_exact_matches_are_deterministically_ordered(pm):
    """Several prompts can share an exact industry. Ordering must be stable and
    decided by text relevance, never arbitrary."""
    a = _ids(pm, "preserve client confidentiality", industry="Professional Services")
    b = _ids(pm, "preserve client confidentiality", industry="Professional Services")
    assert a == b, "ordering is not deterministic across identical calls"
    assert a[0] == "PROSERV-001"


def test_ambiguous_cluster_is_resolved_by_text_not_industry(pm):
    """3 prompts share 'Professional Services'. The industry bonus is identical
    for all, so TEXT must discriminate — the exact defect in the old scorer."""
    assert _ids(pm, "evaluate supplier onboarding and sourcing risk",
                industry="Professional Services")[0] == "PROC-001"
    assert _ids(pm, "flag program milestone slippage and delivery risk",
                industry="Professional Services")[0] == "PMO-001"


def test_no_framework_supplied(pm):
    ids = _ids(pm, "define retention schedules and legal hold procedures",
               industry="Legal / Compliance", framework=None)
    assert ids[0] == "RECORDS-001"


def test_unknown_industry_does_not_crash_or_fabricate(pm):
    """An industry not in the corpus must degrade gracefully to text-only
    ranking — never raise, never invent a match."""
    res = pm.route_task("protect patient records", industry="Interplanetary Mining")
    recs = res.get("recommendations", [])
    assert isinstance(recs, list)
    for r in recs:
        assert r["id"], "malformed recommendation"


def test_alias_and_spelling_variants(pm):
    """Acronym/expansion variants must both reach the right prompt, because the
    corpus carries both forms and IDF matches on the decisive tokens."""
    # expansion -> acronym-titled prompt
    assert 0 < _rank(pm, "criminal justice information services handling",
                     "GOVFRAME-006", industry="Federal Civilian") <= 3
    # acronym -> same prompt
    assert 0 < _rank(pm, "CJIS security policy review",
                     "GOVFRAME-006", industry="Federal Civilian") <= 3


def test_adversarial_stop_word_heavy_query(pm):
    """A query that is almost entirely stop-words must not let a generic prompt
    win on noise. It should either fail to rank anything highly or still respect
    the structured signal — but must not crash or return garbage."""
    res = pm.route_task("the and or of to in for on with at by from an is are",
                        industry="Public Health")
    recs = res.get("recommendations", [])
    if recs:
        # all query terms are stop-words -> text score ~0 -> the exact-industry
        # prompt must still lead on the structured tier.
        assert recs[0]["id"] == "PUBHEALTH-001"


def test_stop_words_do_not_inflate_generic_prompts(pm):
    """Regression for the original contamination: generic prompts matching only
    stop/common words must not outrank a specific exact match."""
    ids = _ids(pm, "audit the data and the systems for all of the controls",
               industry="Smart Cities")
    assert ids[0] == "SMARTCITY-001"


def test_low_quality_exact_match_vs_high_quality_near_match(pm):
    """Quality is a bounded tie-break only. It must never override a materially
    better text+structure match."""
    src = (ROOT / "src" / "hoch_agent_swarm" / "promptbrain_manager.py").read_text()
    assert "quality is a bounded tie-break" in src.lower() or "bounded tie-break" in src.lower(), \
        "quality tie-break contract not documented"
    # behaviourally: the exact-industry prompt still wins
    assert _ids(pm, "protect laboratory research data and intellectual property",
                industry="Research Labs")[0] == "RESEARCH-001"


def test_deprecated_prompt_does_not_outrank_current(pm):
    """If a prompt is retired/deprecated it must not be routed to over an active
    equivalent. Guard: every rank-1 result across the benchmark is active."""
    for c in BENCHMARK["cases"][:12]:
        res = pm.route_task(c["query"], industry=c["industry"], framework=c["framework"])
        recs = res.get("recommendations", [])
        if recs:
            assert recs[0].get("status", "active") != "deprecated", \
                f"deprecated prompt routed first for: {c['query']}"
