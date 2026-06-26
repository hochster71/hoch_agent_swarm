"""
trial_preflight.py — Environment preflight for isolated CrewAI upgrade trials.

Validates that all local runtime requirements are satisfied before a trial
worktree crew run is attempted.  Specifically automates the lesson from
Batch 7: git worktrees do not copy gitignored files, so .env must be
explicitly provided.

Checks (in order):
  1. .env file is present in the current working directory
  2. MODEL env var is set and non-empty (after load_dotenv)
  3. API_BASE env var is set and non-empty
  4. Ollama endpoint at API_BASE is reachable (HTTP GET, 3 s timeout)
  5. At least one baseline run_report.json exists (warn-only)

Usage:
    uv run trial_preflight           # exit 0 = all blocking checks pass
    uv run trial_preflight --json    # machine-readable JSON result

Exit codes:
    0  all blocking checks pass
    1  one or more blocking checks failed
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OLLAMA_TIMEOUT_SECONDS = 3
_RUN_REPORTS_DIR = "artifacts/crew_runs"
_CHECK_ENV_FILE = "env_file_present"
_CHECK_MODEL = "model_env_var_set"
_CHECK_API_BASE = "api_base_env_var_set"
_CHECK_OLLAMA = "ollama_endpoint_reachable"
_CHECK_BASELINE = "baseline_run_report_exists"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Result of a single preflight check."""

    name: str
    passed: bool
    blocking: bool
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PreflightResult:
    """Aggregated result of all preflight checks."""

    passed: bool  # True only if all *blocking* checks pass
    checks: list[CheckResult] = field(default_factory=list)
    baseline_report: Optional[str] = None  # path to latest run_report.json

    def to_dict(self) -> dict:
        d = {
            "passed": self.passed,
            "baseline_report": self.baseline_report,
            "checks": [c.to_dict() for c in self.checks],
        }
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary_lines(self) -> list[str]:
        """Return human-readable lines for terminal output."""
        lines: list[str] = []
        for c in self.checks:
            icon = "✅" if c.passed else ("❌" if c.blocking else "⚠️ ")
            tag = "" if c.blocking else " [warn-only]"
            lines.append(f"  {icon} {c.name}{tag}: {c.detail}")
        lines.append("")
        if self.baseline_report:
            lines.append(f"  baseline: {self.baseline_report}")
        status = "PASS — all blocking checks passed" if self.passed else "BLOCKED — see failures above"
        lines.append(f"\npreflight: {status}")
        return lines


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def _check_env_file(cwd: str) -> CheckResult:
    """Check 1: .env file is present in cwd."""
    env_path = os.path.join(cwd, ".env")
    present = os.path.isfile(env_path)
    return CheckResult(
        name=_CHECK_ENV_FILE,
        passed=present,
        blocking=True,
        detail=f".env found at {env_path}" if present else (
            f".env MISSING at {env_path} — "
            "git worktrees do not copy gitignored files; "
            "run: ln -sf <main-repo>/.env ./.env"
        ),
    )


def _check_model_var(env: dict) -> CheckResult:
    """Check 2: MODEL env var is set and non-empty."""
    value = env.get("MODEL", "").strip()
    passed = bool(value)
    return CheckResult(
        name=_CHECK_MODEL,
        passed=passed,
        blocking=True,
        detail=f"MODEL={value!r}" if passed else "MODEL is not set in .env",
    )


def _check_api_base_var(env: dict) -> CheckResult:
    """Check 3: API_BASE env var is set and non-empty."""
    value = env.get("API_BASE", "").strip()
    passed = bool(value)
    return CheckResult(
        name=_CHECK_API_BASE,
        passed=passed,
        blocking=True,
        detail=f"API_BASE={value!r}" if passed else "API_BASE is not set in .env",
    )


def _check_ollama_endpoint(api_base: str, timeout: int = _OLLAMA_TIMEOUT_SECONDS) -> CheckResult:
    """Check 4: Ollama HTTP endpoint is reachable."""
    url = api_base.rstrip("/")
    try:
        req = urllib.request.urlopen(url, timeout=timeout)  # noqa: S310
        code = req.getcode()
        passed = 200 <= code < 400
        return CheckResult(
            name=_CHECK_OLLAMA,
            passed=passed,
            blocking=True,
            detail=f"HTTP {code} from {url}" if passed else f"HTTP {code} (unexpected) from {url}",
        )
    except urllib.error.HTTPError as e:
        # Some Ollama versions return 200 on GET /, others 404 — treat <500 as reachable
        passed = e.code < 500
        return CheckResult(
            name=_CHECK_OLLAMA,
            passed=passed,
            blocking=True,
            detail=f"HTTP {e.code} from {url}" if passed else (
                f"HTTP {e.code} from {url} — server error, Ollama may not be healthy"
            ),
        )
    except OSError as e:
        return CheckResult(
            name=_CHECK_OLLAMA,
            passed=False,
            blocking=True,
            detail=(
                f"cannot reach {url}: {e} — "
                "is Ollama running? start with: ollama serve"
            ),
        )


def _check_baseline_report(run_reports_dir: str) -> tuple[CheckResult, Optional[str]]:
    """Check 5: at least one baseline run_report.json exists (warn-only)."""
    reports: list[str] = []
    base = Path(run_reports_dir)
    if base.is_dir():
        reports = sorted(
            str(p)
            for p in base.rglob("run_report.json")
        )
    latest = reports[-1] if reports else None
    passed = bool(latest)
    return (
        CheckResult(
            name=_CHECK_BASELINE,
            passed=passed,
            blocking=False,  # warn-only — trial can still run without baseline
            detail=f"latest baseline: {latest}" if passed else (
                f"no run_report.json found under {run_reports_dir} — "
                "run `uv run run_crew` on main first to establish a baseline"
            ),
        ),
        latest,
    )


# ---------------------------------------------------------------------------
# Main preflight runner
# ---------------------------------------------------------------------------


def _load_dotenv_into_dict(cwd: str) -> dict:
    """
    Parse .env in cwd and return its key/value pairs as a dict.
    Uses the stdlib only — does not call load_dotenv() to avoid
    modifying os.environ globally during tests.
    """
    env_path = os.path.join(cwd, ".env")
    result: dict = {}
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    result[key.strip()] = value.strip()
    except OSError:
        pass
    return result


def run_preflight(
    cwd: Optional[str] = None,
    run_reports_dir: Optional[str] = None,
    ollama_timeout: int = _OLLAMA_TIMEOUT_SECONDS,
) -> PreflightResult:
    """
    Execute all preflight checks and return a PreflightResult.

    Args:
        cwd: Working directory to check (default: os.getcwd()).
        run_reports_dir: Where run reports are stored (default: _RUN_REPORTS_DIR).
        ollama_timeout: Seconds to wait for Ollama HTTP response.

    Returns:
        PreflightResult with all check outcomes.
    """
    cwd = cwd or os.getcwd()
    run_reports_dir = run_reports_dir or _RUN_REPORTS_DIR

    checks: list[CheckResult] = []
    blocking_failed = False

    # Check 1 — .env present
    c1 = _check_env_file(cwd)
    checks.append(c1)
    if not c1.passed:
        blocking_failed = True
        # Cannot read env vars without .env — fail fast
        baseline_check, baseline_report = _check_baseline_report(run_reports_dir)
        checks.append(baseline_check)
        return PreflightResult(passed=False, checks=checks, baseline_report=baseline_report)

    # Load env vars from .env (without polluting os.environ)
    env = _load_dotenv_into_dict(cwd)

    # Check 2 — MODEL set
    c2 = _check_model_var(env)
    checks.append(c2)
    if not c2.passed:
        blocking_failed = True

    # Check 3 — API_BASE set
    c3 = _check_api_base_var(env)
    checks.append(c3)
    if not c3.passed:
        blocking_failed = True

    # Check 4 — Ollama reachable (only if API_BASE is available)
    api_base = env.get("API_BASE", "").strip()
    if api_base:
        c4 = _check_ollama_endpoint(api_base, timeout=ollama_timeout)
        checks.append(c4)
        if not c4.passed:
            blocking_failed = True
    else:
        # API_BASE missing — synthesize a failed check 4
        checks.append(CheckResult(
            name=_CHECK_OLLAMA,
            passed=False,
            blocking=True,
            detail="skipped — API_BASE is not set",
        ))
        blocking_failed = True

    # Check 5 — baseline report (warn-only)
    baseline_check, baseline_report = _check_baseline_report(run_reports_dir)
    checks.append(baseline_check)

    return PreflightResult(
        passed=not blocking_failed,
        checks=checks,
        baseline_report=baseline_report,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI entry point for `uv run trial_preflight`.

    Returns 0 if all blocking checks pass, 1 otherwise.
    """
    argv = argv if argv is not None else sys.argv[1:]
    as_json = "--json" in argv

    result = run_preflight()

    if as_json:
        print(result.to_json())
    else:
        for line in result.summary_lines():
            print(line)

    if not result.passed:
        if not as_json:
            print("\nTrial blocked. Fix the issues above before running the crew.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
