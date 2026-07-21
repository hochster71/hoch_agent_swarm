#!/usr/bin/env python3
"""mutation_precondition.py — CYB-004. Environment gate for mutating operations.

THE INVARIANT (founder, 2026-07-21), companion to the CYB-003 observer rule:

    OBSERVER   may not report ABSENCE until it has demonstrated it can detect PRESENCE.
    MUTATOR    may not EXECUTE until its execution environment has been demonstrated
               compatible with the intended SEMANTICS.

WHAT HAPPENED. `npm install --save-dev vite@^6.4.3` was run in a shell where
NODE_ENV=production, which makes npm default to omit=dev. The command:

    - wrote vite ^6.4.3 into package.json                     (manifest mutated)
    - installed nothing                                        (no packages added)
    - REMOVED 64 dev packages including vite itself            (tree destroyed)
    - exited 0 and printed "removed 64 packages in 3s"         (looked like success)

Then both restore attempts inherited the same defect. `npm install` and `npm ci` each
silently omitted dev dependencies, and one reported "up to date" while vite was absent.
Only `--include=dev` worked.

NOT "npm lied". npm behaved exactly as documented. The lesson is narrower and worse:

    AN OPERATION'S SEMANTICS ARE PARTLY DEFINED BY ITS EXECUTION ENVIRONMENT.

The command was correct. The environment silently changed what it meant. This is a
sibling of every other finding today — an artifact (here, the command string) describing
something narrower than the reader assumes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha_file(p: Path) -> Optional[str]:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _cmd(argv: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60,
                           cwd=str(cwd) if cwd else None)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def npm_environment(cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Capture the environment that will DEFINE the semantics of an npm command."""
    d = cwd or (ROOT / "frontend")
    return {
        "node_version": _cmd(["node", "--version"]),
        "npm_version": _cmd(["npm", "--version"]),
        "NODE_ENV": os.environ.get("NODE_ENV"),
        "npm_config_omit": _cmd(["npm", "config", "get", "omit"], d),
        "npm_config_include": _cmd(["npm", "config", "get", "include"], d),
        "npm_config_production": _cmd(["npm", "config", "get", "production"], d),
        "platform": sys.platform,
        "cwd": str(d),
        "package_json_sha256": _sha_file(d / "package.json"),
        "lockfile_sha256": _sha_file(d / "package-lock.json"),
    }


def check_npm_dev_mutation(cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Gate a devDependency mutation. FAIL-CLOSED.

    The specific check that would have prevented CYB-004: if NODE_ENV=production or
    npm's omit config includes "dev", a --save-dev install will edit the manifest and
    then remove the very packages it claims to add.
    """
    env = npm_environment(cwd)
    failures: List[str] = []

    if env["node_version"] is None:
        failures.append("node not available — cannot establish environment")
    if env["npm_version"] is None:
        failures.append("npm not available — cannot establish environment")

    omit = (env.get("npm_config_omit") or "").lower()
    if env.get("NODE_ENV") == "production":
        failures.append(
            "NODE_ENV=production — npm defaults to omit=dev. A --save-dev install will "
            "write the manifest and REMOVE dev packages. Use --include=dev, or run with "
            "NODE_ENV unset/development.")
    if "dev" in omit:
        failures.append(f"npm config omit={omit!r} excludes dev dependencies")
    if str(env.get("npm_config_production")).lower() == "true":
        failures.append("npm config production=true excludes dev dependencies")

    if env["lockfile_sha256"] is None:
        failures.append("no package-lock.json — no rollback anchor for this mutation")

    ok = not failures
    return {
        "schema_version": "HELM_MUTATION_PRECONDITION_v1",
        "operation": "npm devDependency mutation",
        "checked_at": _now(),
        "execution_environment": env,
        "precondition_status": "PASS" if ok else "BLOCKED",
        "failures": failures,
        "mutation_authorized": ok,
        "remedy": None if ok else
                  "re-run with --include=dev, or unset NODE_ENV for this operation",
        "note": ("an operation's semantics are partly defined by its execution "
                 "environment; a correct command in the wrong environment is a "
                 "different operation"),
    }


def require_authorized(cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Raise unless the environment is demonstrated compatible. Fail-closed."""
    r = check_npm_dev_mutation(cwd)
    if not r["mutation_authorized"]:
        raise RuntimeError("DEPENDENCY MUTATION BLOCKED: " + "; ".join(r["failures"]))
    return r


if __name__ == "__main__":  # pragma: no cover
    res = check_npm_dev_mutation()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["mutation_authorized"] else 1)
