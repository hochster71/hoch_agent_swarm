"""Hermetic event ledger for the frozen helm_runtime suites (G3/T9 fix, 2026-07-20).

test_commit_emits_event (FROZEN — d8d5139a) asserts its event appears in the last 5
entries of the event ledger. Against the SHARED production ledger this is order-dependent
(other tests and the LIVE runtime append concurrently) and pollutes real evidence.

The frozen transaction.py explicitly resolves the event-bus path at call time "so tests
can monkeypatch EVENTS_PATH" — this fixture is that sanctioned composition point:
per-test tmp ledger for both publish (module attr, call-time resolved) and tail_events
(definition-time default, wrapped). No frozen bytes change.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _hermetic_event_ledger(tmp_path, monkeypatch):
    import backend.helm_runtime.event_bus as eb

    ledger = tmp_path / "helm_events.jsonl"
    monkeypatch.setattr(eb, "EVENTS_PATH", ledger)
    _orig_tail = eb.tail_events
    monkeypatch.setattr(
        eb, "tail_events",
        lambda n=20, path=None: _orig_tail(n=n, path=path if path is not None else ledger),
    )
    yield
