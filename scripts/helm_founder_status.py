#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


STATUS_KEYS = (
    "status",
    "state",
    "result",
    "decision",
    "posture",
    "outcome",
    "promotion_state",
    "validation_state",
)

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
}


@dataclass
class Observation:
    control_id: str
    status: str
    source: str
    detail: str


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def git_value(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def iter_json_files(root: Path) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            if filename.endswith((".json", ".jsonl")):
                yield Path(current_root) / filename


def extract_status_from_mapping(mapping: dict[str, Any]) -> str:
    for key in STATUS_KEYS:
        if key in mapping:
            return normalize(mapping[key])

    for key, value in mapping.items():
        lowered = key.lower()
        if any(token in lowered for token in ("validated", "resolved", "complete", "passed")):
            if isinstance(value, bool):
                return "PASS" if value else "FAIL"

    return "UNKNOWN"


def find_control_in_object(
    obj: Any,
    control_id: str,
    source: Path,
    path: str = "$",
) -> list[Observation]:
    findings: list[Observation] = []

    if isinstance(obj, dict):
        object_text = json.dumps(obj, sort_keys=True, default=str).upper()
        explicit_id = any(
            normalize(obj.get(key)) == normalize(control_id)
            for key in ("id", "control", "control_id", "risk_id", "name")
            if key in obj
        )

        if explicit_id or control_id.upper() in object_text:
            status = extract_status_from_mapping(obj)
            detail = f"matched at {path}"
            findings.append(
                Observation(
                    control_id=control_id,
                    status=status,
                    source=str(source),
                    detail=detail,
                )
            )

        for key, value in obj.items():
            findings.extend(
                find_control_in_object(value, control_id, source, f"{path}.{key}")
            )

    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            findings.extend(
                find_control_in_object(value, control_id, source, f"{path}[{index}]")
            )

    return findings


def scan_control(root: Path, control_id: str) -> list[Observation]:
    observations: list[Observation] = []

    for path in iter_json_files(root):
        try:
            if path.suffix == ".jsonl":
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        line = line.strip()
                        if not line or control_id.upper() not in line.upper():
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            observations.append(
                                Observation(
                                    control_id=control_id,
                                    status="UNKNOWN",
                                    source=str(path),
                                    detail=f"malformed matching JSONL record at line {line_number}",
                                )
                            )
                            continue
                        observations.extend(
                            find_control_in_object(
                                obj,
                                control_id,
                                path,
                                f"$[line:{line_number}]",
                            )
                        )
            else:
                raw = path.read_text(encoding="utf-8", errors="replace")
                if control_id.upper() not in raw.upper():
                    continue
                observations.extend(
                    find_control_in_object(load_json(path), control_id, path)
                )
        except Exception as exc:
            observations.append(
                Observation(
                    control_id=control_id,
                    status="UNKNOWN",
                    source=str(path),
                    detail=f"read error: {exc}",
                )
            )

    return observations


def choose_observation(
    observations: list[Observation],
    green_states: set[str],
    blocked_states: set[str],
) -> Observation:
    if not observations:
        return Observation(
            control_id="UNKNOWN",
            status="UNKNOWN",
            source="NO EVIDENCE FOUND",
            detail="No matching control record was located",
        )

    ranked: list[tuple[int, Observation]] = []
    for item in observations:
        state = normalize(item.status)
        if state in blocked_states:
            rank = 3
        elif state in green_states:
            rank = 2
        else:
            rank = 1
        ranked.append((rank, item))

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return ranked[0][1]


def classify(status: str, green_states: set[str]) -> str:
    return "GREEN" if normalize(status) in green_states else "BLOCKED"


def progress_bar(percent: float, width: int = 50) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int(round((percent / 100.0) * width))
    return "█" * filled + "░" * (width - filled)


def section(title: str) -> None:
    print()
    print(title)
    print("─" * 92)


def discover_runtime_sources(root: Path) -> list[str]:
    candidates = [
        "coordination/coordination_bus.json",
        "coordination/helm_runtime_datalinks_summary.json",
        "has_live_project_tracker/data/active_runtime_source.json",
        "has_live_project_tracker/data/helm_execution_log.json",
        "has_live_project_tracker/data/helm_task_queue.json",
        "has_live_project_tracker/data/goal_blocker_register.json",
        "has_live_project_tracker/data/orchestration_bridge_control.json",
    ]
    return [item for item in candidates if (root / item).exists()]


def determine_next_action(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return "Review and execute the final founder promotion gate."

    priority = ["GOV-007", "ACTOR-F3", "RISK-DEP-001", "ACTOR-F2", "ACTOR-001"]
    blocker_ids = {item["id"] for item in blockers}

    for control_id in priority:
        if control_id in blocker_ids:
            actions = {
                "GOV-007": "Apply the disposable-branch protection and run the real GOV-007 adversarial push.",
                "ACTOR-F3": "Complete credential-custody evidence, including Keychain ACL and signing-key custody.",
                "RISK-DEP-001": "Triage and disposition the registered critical and high dependency vulnerabilities.",
                "ACTOR-F2": "Complete the remaining actor inventory, including the GitHub Actions execution context.",
                "ACTOR-001": "Reconcile the authoritative ACTOR-001 record with the completed F2 observations.",
            }
            return actions[control_id]

    return f"Resolve {blockers[0]['id']}: {blockers[0]['description']}."


def render(root: Path, contract_path: Path) -> int:
    contract = load_json(contract_path)
    green_states = {normalize(item) for item in contract["green_states"]}
    blocked_states = {normalize(item) for item in contract["blocked_states"]}

    results: list[dict[str, Any]] = []
    total_weight = 0.0
    earned_weight = 0.0

    for control in contract["required_controls"]:
        control_id = control["id"]
        weight = float(control.get("weight", 1))
        observations = scan_control(root, control_id)
        selected = choose_observation(observations, green_states, blocked_states)
        state = normalize(selected.status)
        disposition = classify(state, green_states)

        total_weight += weight
        if disposition == "GREEN":
            earned_weight += weight

        results.append(
            {
                **control,
                "status": state,
                "disposition": disposition,
                "source": selected.source,
                "detail": selected.detail,
                "observation_count": len(observations),
            }
        )

    completion = (earned_weight / total_weight * 100.0) if total_weight else 0.0
    blockers = [item for item in results if item["disposition"] != "GREEN"]

    # No fake green: 100% is impossible while any required control is unresolved.
    if blockers and completion >= 100.0:
        completion = 99.0

    head = git_value(root, "rev-parse", "HEAD")
    branch = git_value(root, "branch", "--show-current")
    dirty = git_value(root, "status", "--porcelain")
    tree_state = "CLEAN" if dirty == "" else "DIRTY"
    timestamp = datetime.now(timezone.utc).isoformat()

    print("╔" + "═" * 90 + "╗")
    print("║" + " HELM FOUNDER CONSOLE ".center(90) + "║")
    print("║" + " ONE COMMAND · ONE STATUS MODEL · ONE FOUNDER VIEW ".center(90) + "║")
    print("╚" + "═" * 90 + "╝")

    section("MISSION")
    print(f"Repository       {root}")
    print(f"Branch           {branch}")
    print(f"HEAD             {head}")
    print(f"Working tree     {tree_state}")
    print(f"Generated UTC    {timestamp}")

    section("BURNDOWN TO 100%")
    print(progress_bar(completion))
    print(f"{completion:6.1f}% COMPLETE    {100.0 - completion:6.1f}% REMAINING")
    print(f"Resolved weight  {earned_weight:.0f} / {total_weight:.0f}")
    print(f"Open controls    {len(blockers)} / {len(results)}")

    section("CRITICAL CONTROLS")
    for item in results:
        marker = "✓" if item["disposition"] == "GREEN" else "!"
        print(
            f"{marker} {item['id']:<14} "
            f"{item['status']:<22} "
            f"{item['description']}"
        )

    section("CRITICAL PATH")
    if blockers:
        for index, item in enumerate(blockers, start=1):
            print(f"{index}. {item['id']} — {item['status']} — {item['description']}")
    else:
        print("No unresolved required controls detected.")

    section("FOUNDER-ONLY GATES")
    print("Spend approval            FOUNDER ONLY")
    print("Secret provisioning       FOUNDER ONLY")
    print("Signing and submission    FOUNDER ONLY")
    print("Money movement            FOUNDER ONLY")
    print("Final promotion           " + ("READY FOR REVIEW" if not blockers else "LOCKED"))

    section("RUNTIME AND EVIDENCE")
    runtime_sources = discover_runtime_sources(root)
    if runtime_sources:
        for source in runtime_sources:
            print(f"OBSERVED       {source}")
    else:
        print("UNKNOWN        No recognized runtime source files found")

    section("SECURITY AND RISK")
    security_ids = {"ACTOR-001", "ACTOR-F2", "ACTOR-F3", "GOV-007", "RISK-DEP-001"}
    for item in results:
        if item["id"] in security_ids:
            print(f"{item['id']:<14} {item['status']:<22} {item['source']}")

    section("PROMOTION")
    if blockers:
        print("Promotion state  BLOCKED")
        print("Reason           Required evidence-backed controls remain unresolved.")
    else:
        print("Promotion state  READY FOR FOUNDER REVIEW")
        print("Reason           All required baseline controls are evidence-backed and green.")

    section("NEXT FOUNDER ACTION")
    print(determine_next_action(blockers))

    section("EVIDENCE SOURCES")
    for item in results:
        print(f"{item['id']:<14} {item['source']}")
        print(f"{'':14} {item['detail']}")

    section("NO FAKE GREEN")
    print("Unknown remains UNKNOWN.")
    print("Blocked remains BLOCKED.")
    print("Snapshots certify state; histories certify behavior.")
    print("100% is prohibited while any required control lacks qualifying evidence.")

    return 0 if not blockers else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Canonical evidence-derived HELM Founder Status Console"
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="HELM repository root",
    )
    parser.add_argument(
        "--contract",
        default=None,
        help="Founder-console contract path",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    contract_path = (
        Path(args.contract).expanduser().resolve()
        if args.contract
        else root / "config" / "helm_founder_status_contract.json"
    )

    if not contract_path.exists():
        print(f"ERROR: contract not found: {contract_path}", file=sys.stderr)
        return 3

    return render(root, contract_path)


if __name__ == "__main__":
    raise SystemExit(main())
