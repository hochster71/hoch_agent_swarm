"""
quality_gate.py — Local CI quality gate for hoch_agent_swarm.

Runs the full project validation suite locally without any cloud dependency.
Equivalent to what a CI pipeline would enforce, but runnable on any
developer machine with Ollama running.

Gate steps (always run in order):
  1. import_check   — verify the package imports cleanly
  2. preflight      — run trial_preflight (env, MODEL, Ollama, model availability)
  3. pytest         — run full test suite via `uv run pytest -q`
  4. live_crew      — run `uv run run_crew` (ONLY with --live flag; skipped otherwise)

Usage:
    uv run quality_gate              # steps 1-3 only
    uv run quality_gate --live       # steps 1-4 (runs the crew; takes ~minutes)
    uv run quality_gate --json       # machine-readable JSON output
    uv run quality_gate --live --json

Exit codes:
    0  PASS — all included steps passed
    1  FAIL — one or more steps failed

Design principles:
  - Steps run unconditionally in sequence (no short-circuit) so the full
    failure picture is always visible.
  - Exception: step 4 (live_crew) only runs when --live is explicitly passed.
  - No cloud APIs. No external model providers. Ollama only.
  - All subprocess stderr is captured and surfaced in StepResult.detail
    on failure so the gate output is self-contained.
"""

from __future__ import annotations

import json
import subprocess
import sys

from dataclasses import asdict, dataclass, field
from typing import Optional

from hoch_agent_swarm.trial_preflight import PreflightResult, run_preflight


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STEP_IMPORT = "import_check"
_STEP_PREFLIGHT = "preflight"
_STEP_PYTEST = "pytest"
_STEP_LIVE_CREW = "live_crew"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Result of a single quality gate step."""

    name: str
    passed: bool
    detail: str          # human-readable summary
    output: str = ""     # captured stdout/stderr (trimmed)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GateResult:
    """Aggregated result of all quality gate steps."""

    passed: bool
    live_run_included: bool
    steps: list[StepResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "live_run_included": self.live_run_included,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary_lines(self) -> list[str]:
        """Return human-readable terminal output lines."""
        lines: list[str] = []
        for s in self.steps:
            icon = "✅" if s.passed else "❌"
            lines.append(f"  {icon} {s.name}: {s.detail}")
            if not s.passed and s.output:
                # Indent captured output under the failed step
                for out_line in s.output.splitlines()[-20:]:  # last 20 lines
                    lines.append(f"      {out_line}")
        lines.append("")
        verdict = "PASS" if self.passed else "FAIL"
        icon = "✅" if self.passed else "❌"
        live_tag = " (live crew included)" if self.live_run_included else " (live crew skipped)"
        lines.append(f"quality_gate: {icon} {verdict}{live_tag}")
        return lines


# ---------------------------------------------------------------------------
# Individual gate step functions
# ---------------------------------------------------------------------------


def _run_import_check() -> StepResult:
    """
    Step 1: Verify the package imports without errors.

    Uses subprocess so import side-effects are isolated from the
    gate runner process itself.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import hoch_agent_swarm; print('ok')"],
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    combined = (result.stdout + result.stderr).strip()
    return StepResult(
        name=_STEP_IMPORT,
        passed=passed,
        detail="package imports cleanly" if passed else "import failed",
        output=combined if not passed else "",
    )


def _run_preflight_step() -> StepResult:
    """
    Step 2: Run trial_preflight checks.

    Calls run_preflight() directly (no subprocess) so the gate can
    surface per-check detail without re-parsing output.
    """
    result: PreflightResult = run_preflight()
    passed = result.passed

    if passed:
        detail = f"all {len(result.checks)} preflight checks passed"
    else:
        failed = [c for c in result.checks if c.blocking and not c.passed]
        names = ", ".join(c.name for c in failed)
        detail = f"BLOCKED — failed: {names}"

    # Build a compact summary of all checks for the output field
    check_lines = []
    for c in result.checks:
        icon = "✅" if c.passed else ("❌" if c.blocking else "⚠️ ")
        tag = " [warn]" if not c.blocking else ""
        check_lines.append(f"{icon} {c.name}{tag}: {c.detail}")

    return StepResult(
        name=_STEP_PREFLIGHT,
        passed=passed,
        detail=detail,
        output="\n".join(check_lines) if not passed else "",
    )


def _run_pytest_step() -> StepResult:
    """
    Step 3: Run the full test suite via `uv run pytest -q`.

    Captures output. On failure, surfaces the last 30 lines so the
    gate report is self-contained.
    """
    result = subprocess.run(
        ["uv", "run", "pytest", "-q", "--tb=short"],
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    combined = (result.stdout + result.stderr).strip()

    # Extract summary line (last non-empty line)
    summary = ""
    for line in reversed(combined.splitlines()):
        if line.strip():
            summary = line.strip()
            break

    return StepResult(
        name=_STEP_PYTEST,
        passed=passed,
        detail=summary if summary else ("all tests passed" if passed else "tests failed"),
        output=combined if not passed else "",
    )


def _run_live_crew_step() -> StepResult:
    """
    Step 4 (optional): Run the crew end-to-end via `uv run run_crew`.

    Only called when --live is explicitly passed. Takes several minutes.
    Captures output; surfaces last 30 lines on failure.
    """
    result = subprocess.run(
        ["uv", "run", "run_crew"],
        capture_output=True,
        text=True,
        timeout=1200,  # 20-minute hard timeout
    )
    passed = result.returncode == 0
    combined = (result.stdout + result.stderr).strip()

    # Look for run report path in output
    report_line = ""
    for line in combined.splitlines():
        if "run_report.json" in line or "Run report" in line:
            report_line = line.strip()
            break

    detail = (
        f"crew run PASS — {report_line}" if passed and report_line
        else "crew run PASS" if passed
        else "crew run FAIL"
    )

    return StepResult(
        name=_STEP_LIVE_CREW,
        passed=passed,
        detail=detail,
        output=combined[-3000:] if not passed else "",  # last ~3000 chars on failure
    )


# ---------------------------------------------------------------------------
# Main gate runner
# ---------------------------------------------------------------------------


def run_quality_gate(include_live: bool = False) -> GateResult:
    """
    Execute all quality gate steps and return a GateResult.

    Args:
        include_live: If True, step 4 (live crew run) is included.

    Returns:
        GateResult with per-step outcomes and overall verdict.

    Steps run unconditionally — no short-circuit — so the full failure
    picture is always available even when multiple steps fail.
    """
    steps: list[StepResult] = []

    steps.append(_run_import_check())
    steps.append(_run_preflight_step())
    steps.append(_run_pytest_step())

    if include_live:
        steps.append(_run_live_crew_step())

    overall_passed = all(s.passed for s in steps)

    return GateResult(
        passed=overall_passed,
        live_run_included=include_live,
        steps=steps,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI entry point for `uv run quality_gate`.

    Flags:
        --live    Include live crew run (step 4)
        --json    Machine-readable JSON output

    Returns 0 for PASS, 1 for FAIL.
    """
    argv = argv if argv is not None else sys.argv[1:]
    include_live = "--live" in argv
    as_json = "--json" in argv

    result = run_quality_gate(include_live=include_live)

    if as_json:
        print(result.to_json())
    else:
        for line in result.summary_lines():
            print(line)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
