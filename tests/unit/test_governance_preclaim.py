"""Governance pre-claim enforcement — EDR-0010 §4.

Founder rule, 2026-07-20:

    Every strategic proposal submitted to the HELM Council must pass the same pre-claim
    verification process required of software, evidence, and runtime claims. A governance
    proposal cannot assume repository state; it must cite the authoritative constitutional
    artifacts it extends, or explicitly state that it did not verify them.

    Governance is evidence-backed engineering, not an exception to it.

This file makes that rule executable. It is the reason the rule exists at all: the "HELM
JANUS" proposal of 2026-07-20 asserted the repository held only "folder-level references
rather than substantive architecture documents" while the constitution, design
constitution, council charter, canonical runtime, control-surface map, and ten EDRs were
all present. A prose rule would not have caught the next one.

Known non-compliance at authoring time (2026-07-20) is listed in GRANDFATHERED. Entries
are debts, not exemptions: each should be repaired and removed from the list.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EDR_DIR = ROOT / "docs" / "helm" / "edr"

# Authoritative constitutional artifacts. A governance proposal must cite at least one,
# or explicitly record that it did not verify repository state.
CONSTITUTIONAL = [
    "HELM_CONSTITUTION",
    "HELM_DESIGN_CONSTITUTION",
    "COUNCIL_RUNTIME_CHARTER",
    "HELM_CANONICAL_RUNTIME",
    "CONTROL_SURFACE_MAP",
]

NON_VERIFICATION_DISCLOSURE = re.compile(
    r"(did not verify|not verified|unverified repository state|no pre-claim)", re.I
)

# Pre-existing debt as of EDR-0010. Do not add to this list; repair and remove instead.
GRANDFATHERED = {
    "EDR-0001-executive-runtime-four-engines.md",
    "EDR-0001-runtime-bridge.md",
    "EDR-0002-provider-dispatch-gateway.md",
}


def _edrs():
    if not EDR_DIR.exists():
        pytest.skip("EDR directory absent in this checkout")
    return sorted(EDR_DIR.glob("EDR-*.md"))


def _edr_id(p: Path) -> str:
    m = re.match(r"(EDR-\d+)", p.name)
    return m.group(1) if m else p.stem


# --- the rule -----------------------------------------------------------------

@pytest.mark.parametrize("path", _edrs(), ids=lambda p: p.name)
def test_governance_record_cites_what_it_extends(path):
    """Each EDR must cite a constitutional artifact or disclose non-verification."""
    if path.name in GRANDFATHERED:
        pytest.xfail(f"pre-existing debt logged in EDR-0010: {path.name}")
    text = path.read_text(encoding="utf-8")
    cited = [c for c in CONSTITUTIONAL if c in text]
    disclosed = bool(NON_VERIFICATION_DISCLOSURE.search(text))
    assert cited or disclosed, (
        f"{path.name} proposes governance without citing any authoritative artifact "
        f"({', '.join(CONSTITUTIONAL)}) and without disclosing that repository state was "
        "not verified. A governance proposal may not assume repository state."
    )


@pytest.mark.parametrize("path", _edrs(), ids=lambda p: p.name)
def test_governance_record_declares_status_and_ratification(path):
    """An unratified proposal must say so; silence reads as authority."""
    if path.name in GRANDFATHERED:
        pytest.xfail(f"pre-existing debt logged in EDR-0010: {path.name}")
    text = path.read_text(encoding="utf-8")
    assert re.search(r"^\s*-?\s*\*\*Status:\*\*|^Status:", text, re.M | re.I), (
        f"{path.name} declares no Status; a record with no status is indistinguishable "
        "from a ratified one"
    )


def test_edr_ids_are_unique():
    """Two decisions sharing an ID means the ID resolves to nothing.

    Found by applying this rule to the chain itself: EDR-0001 is used twice.
    """
    by_id = defaultdict(list)
    for p in _edrs():
        by_id[_edr_id(p)].append(p.name)
    dupes = {k: v for k, v in by_id.items() if len(v) > 1}
    assert not dupes, (
        "duplicate EDR identifiers — each ID must resolve to exactly one decision:\n"
        + "\n".join(f"  {k}: {', '.join(v)}" for k, v in sorted(dupes.items()))
    )


# --- the debt must shrink, not grow -------------------------------------------

def test_grandfathered_debt_does_not_grow():
    """New records get no exemption. This is the ratchet."""
    offenders = []
    for p in _edrs():
        if p.name in GRANDFATHERED:
            continue
        text = p.read_text(encoding="utf-8")
        if not any(c in text for c in CONSTITUTIONAL) and not NON_VERIFICATION_DISCLOSURE.search(text):
            offenders.append(p.name)
    assert not offenders, (
        f"non-grandfathered records failing the pre-claim rule: {offenders}. "
        "Cite the artifacts extended, or disclose non-verification — do not add to "
        "GRANDFATHERED."
    )


def test_grandfathered_entries_still_exist():
    """If a debt is repaired, remove it from the list rather than leaving it stale."""
    names = {p.name for p in _edrs()}
    stale = GRANDFATHERED - names
    assert not stale, (
        f"GRANDFATHERED references records that no longer exist: {sorted(stale)}. "
        "Remove them so the debt list stays honest."
    )


# --- self-application ---------------------------------------------------------

def test_this_rules_own_edr_complies():
    """EDR-0010 introduced the rule; it must satisfy it."""
    p = EDR_DIR / "EDR-0010-dual-horizon-doctrine.md"
    if not p.exists():
        pytest.skip("EDR-0010 not present")
    text = p.read_text(encoding="utf-8")
    cited = [c for c in CONSTITUTIONAL if c in text]
    assert len(cited) >= 2, (
        "the EDR that introduces the governance pre-claim rule must itself cite the "
        f"artifacts it extends; found {cited}"
    )
