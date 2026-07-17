"""Mission Store — versioned read + optimistic-concurrency commit.

The Executive Mission is a versioned object. Every worker reads it, proposes a
patch against the version it read, and commits. If another worker committed in
between, the parent_version no longer matches and the commit is refused
(compare-and-swap). This is the "Git-like" concurrency Michael specified:
workers submit a requested change against a known parent; the runtime merges or
rejects — it never silently clobbers.

This module is a thin, dependency-light surface over transaction.py so the
bridge (role_router / bridge_api) and tests share one OCC code path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.helm_runtime.transaction import EXEC_PATH, commit_proposal

ROOT = Path(__file__).resolve().parents[2]


def read_mission(path: Path = EXEC_PATH) -> Dict[str, Any]:
    """Return the full mission object, or an explicit error stub (never a fake)."""
    if not path.exists():
        return {"error": "MISSION_ABSENT", "path": str(path), "mission_version": None}
    return json.loads(path.read_text(encoding="utf-8"))


def current_version(path: Path = EXEC_PATH) -> Optional[int]:
    """The version a worker must pin its proposal to. None if mission absent."""
    doc = read_mission(path)
    v = doc.get("mission_version")
    return int(v) if isinstance(v, int) else None


def read_for_update(path: Path = EXEC_PATH) -> Tuple[Dict[str, Any], Optional[int]]:
    """Read the mission and the version to pin a subsequent commit against."""
    doc = read_mission(path)
    v = doc.get("mission_version")
    return doc, (int(v) if isinstance(v, int) else None)


def commit(
    role: str,
    patch: Dict[str, Any],
    *,
    expected_parent_version: Optional[int] = None,
    path: Path = EXEC_PATH,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Compare-and-swap commit.

    If ``expected_parent_version`` is provided, the commit only lands when the
    on-disk version still equals it; otherwise it returns status ``CONFLICT``
    with both versions so the caller can re-read and retry. Passing ``None``
    performs a last-writer commit (allowed, but callers on the bridge always
    pin a version).
    """
    return commit_proposal(
        role,
        patch,
        expected_parent_version=expected_parent_version,
        path=path,
        **kwargs,
    )


def compare_and_swap(
    role: str,
    patch: Dict[str, Any],
    expected_parent_version: int,
    *,
    path: Path = EXEC_PATH,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Explicit CAS: caller MUST supply the version it read. Alias of commit()."""
    return commit(
        role,
        patch,
        expected_parent_version=int(expected_parent_version),
        path=path,
        **kwargs,
    )
