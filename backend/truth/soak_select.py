"""F-A2: select the authoritative soak package.

Rules (never filename glob order alone):
  1. Only HELM-SOAK-(2H|8H|24H|72H)-* phase packages (exclude XH smoke).
  2. Prefer an active IN_PROGRESS package (no seal_verdict yet, or snapshot IN_PROGRESS).
  3. Among sealed packages, pick the latest by seal_verdict.sealed_at (not name sort).
  4. Fall back to soak_config.started_at, then mtime.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
PKGS = ROOT / "coordination" / "council" / "live_proof_packages"
PHASE_RE = re.compile(r"^HELM-SOAK-(2H|8H|24H|72H)-\d{8}T\d{6}Z$")


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _started_at(pkg: Path) -> str:
    cfg = _read_json(pkg / "soak_config.json")
    return str(cfg.get("started_at") or "")


def _sealed_at(pkg: Path) -> str:
    seal = pkg / "seal_verdict.json"
    if not seal.exists():
        return ""
    d = _read_json(seal)
    return str(d.get("sealed_at") or "")


def _is_in_progress(pkg: Path) -> bool:
    """True when the package is a live phase run not yet sealed."""
    if (pkg / "seal_verdict.json").exists():
        return False
    # Prefer explicit snapshot status when present
    snap = pkg / "runtime_truth_snapshots.jsonl"
    if snap.exists():
        lines = [ln for ln in snap.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            try:
                last = json.loads(lines[-1])
                st = str(last.get("soak_status") or "").upper()
                if st == "IN_PROGRESS":
                    return True
                if st in ("COMPLETE", "FAILED", "PASS", "FAIL"):
                    return False
            except Exception:
                pass
    # Unsealed phase package with a config is treated as active
    return (pkg / "soak_config.json").exists()


def list_phase_packages(pkgs_root: Optional[Path] = None) -> list[Path]:
    root = pkgs_root or PKGS
    if not root.exists():
        return []
    return [d for d in root.iterdir() if d.is_dir() and PHASE_RE.match(d.name)]


def select_soak_package(pkgs_root: Optional[Path] = None) -> Optional[Path]:
    """Return the authoritative phase soak package path, or None."""
    phases = list_phase_packages(pkgs_root)
    if not phases:
        return None

    active = [p for p in phases if _is_in_progress(p)]
    if active:
        # newest active by started_at then mtime
        active.sort(key=lambda p: (_started_at(p), p.stat().st_mtime))
        return active[-1]

    sealed = [p for p in phases if (p / "seal_verdict.json").exists()]
    if sealed:
        sealed.sort(key=lambda p: (_sealed_at(p) or _started_at(p), p.stat().st_mtime))
        return sealed[-1]

    # Unsealed but not clearly in progress — last resort by started_at/mtime
    phases.sort(key=lambda p: (_started_at(p), p.stat().st_mtime))
    return phases[-1]
