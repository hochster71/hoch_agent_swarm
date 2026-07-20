#!/usr/bin/env python3
"""Harvest a full-suite proof-run log into a candidate-identity-bound artifact (v1).

Council directive (2026-07-20): a full-suite result is accepted ONLY from its actual
final artifact, judged from actual output, never from expectation. This script assembles
that artifact mechanically — full SHA (never abbreviated), worktree/index cleanliness,
untracked manifest, environment hashes (uv.lock / pyproject.toml), the exact pytest
command, timestamps, the parsed summary, and the verbatim failure list — and preserves
the raw log immutably alongside it.

Usage:  .venv/bin/python scripts/goal/harvest_full_suite_proof.py <log_path> [--label NAME]
Exit:   0 = artifact written (regardless of test outcome — honesty over green)
        2 = log missing/unparseable (fail-closed: no artifact)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "coordination/evidence/sbom_cve_20260719/runtime"
ORIGINALS = OUT_DIR / "originals"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=60)
    return r.stdout


def _iso(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log_path")
    ap.add_argument("--label", default="full_suite_proof")
    ap.add_argument("--pytest-command", default=".venv/bin/python -m pytest tests/ -q --tb=no -p no:cacheprovider")
    a = ap.parse_args()
    log = Path(a.log_path)
    if not log.is_file():
        print(f"FAIL-CLOSED: log not found: {log}", file=sys.stderr)
        return 2

    text = log.read_text(errors="replace")
    lines = [l for l in text.splitlines() if l.strip()]
    tail = lines[-1] if lines else ""

    interrupted = bool(re.search(r"Interrupted: .* during collection", text))
    summary = {}
    for key, pat in (("passed", r"(\d+) passed"), ("failed", r"(\d+) failed"),
                     ("errored", r"(\d+) error"), ("skipped", r"(\d+) skipped"),
                     ("warnings", r"(\d+) warning")):
        m = re.search(pat, tail)
        summary[key] = int(m.group(1)) if m else 0
    md = re.search(r"in ([\d.]+)s(?: \(([\d:]+)\))?", tail)
    summary["duration_seconds"] = float(md.group(1)) if md else None
    if not tail or (not interrupted and not re.search(r"(passed|failed|error|no tests ran)", tail)):
        print(f"FAIL-CLOSED: cannot parse a pytest terminal line from {log} (tail={tail!r})", file=sys.stderr)
        return 2

    failed_ids = re.findall(r"^FAILED (\S+)", text, re.M)
    error_mods = re.findall(r"^ERROR (\S+)", text, re.M)
    # with -rs, pytest lists skip identities: "SKIPPED [1] tests/foo.py:12: reason"
    skipped_entries = [{"location": m.group(1), "reason": m.group(2)[:160]}
                       for m in re.finditer(r"^SKIPPED \[\d+\] ([^:]+):\d*:? ?(.*)$", text, re.M)]

    porcelain = _git("status", "--porcelain")
    untracked = sorted(l[3:] for l in porcelain.splitlines() if l.startswith("??"))
    worktree_clean = porcelain.strip() == ""
    index_clean = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0

    stat = log.stat()
    started_at = _iso(getattr(stat, "st_birthtime", stat.st_mtime))
    completed_at = _iso(stat.st_mtime)

    log_sha = _sha256(log)
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    preserved = ORIGINALS / f"{a.label}_{log_sha[:12]}.log"
    if not preserved.exists():
        shutil.copy2(log, preserved)
    elif _sha256(preserved) != log_sha:
        print(f"FAIL-CLOSED: {preserved} exists with different content", file=sys.stderr)
        return 2

    artifact = {
        "schema": "HELM_FULL_SUITE_PROOF_v1",
        "label": a.label,
        "verdict_note": "artifact records ACTUAL output; acceptance is judged elsewhere against it",
        "candidate_identity": {
            "head_sha_full": _git("rev-parse", "HEAD").strip(),
            "worktree_clean": worktree_clean,
            "index_clean": index_clean,
            "dirty_entry_count": len(porcelain.splitlines()),
            "tracked_diff_sha256": (None if worktree_clean else hashlib.sha256(_git("diff").encode()).hexdigest()),
            "untracked_file_count": len(untracked),
            "untracked_manifest_sha256": (None if worktree_clean else hashlib.sha256("\n".join(untracked).encode()).hexdigest()),
            "promotion_binding_eligible": worktree_clean,
            "qualification_note": (None if worktree_clean else
                "PRE-FREEZE PROOF against HEAD + working-tree changes — NOT a clean-candidate qualification run"),
        },
        "environment_identity": {
            "uv_lock_sha256": _sha256(ROOT / "uv.lock"),
            "pyproject_toml_sha256": _sha256(ROOT / "pyproject.toml"),
            "python": subprocess.run([str(ROOT / ".venv/bin/python"), "--version"], capture_output=True, text=True).stdout.strip(),
        },
        "execution": {
            "pytest_command": a.pytest_command,
            "started_at": started_at,
            "completed_at": completed_at,
            "log_path_original": str(log),
            "log_preserved_as": str(preserved.relative_to(ROOT)),
            "log_sha256": log_sha,
        },
        "result": {
            "collection_interrupted": interrupted,
            "terminal_line": tail,
            **summary,
            "failed_test_ids": failed_ids,
            "collection_error_modules": error_mods,
            "skipped_entries": skipped_entries or None,
        },
        "harvested_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    out = OUT_DIR / f"{a.label}_artifact.json"
    # control 3 (2026-07-20): atomic write - tmp + fsync + rename; a crash or concurrent
    # reader can never observe a truncated artifact (the confirmation_result.json lesson)
    import os as _os, tempfile as _tf
    fd, tmp = _tf.mkstemp(dir=str(OUT_DIR))
    with _os.fdopen(fd, "w") as f:
        json.dump(artifact, f, indent=2); f.flush(); _os.fsync(f.fileno())
    _os.replace(tmp, str(out))
    print(json.dumps(artifact, indent=2))
    print(f"\nartifact -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
