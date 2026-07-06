#!/usr/bin/env python3
"""HOCH fleet reconciler — DRY-RUN, RECOMMEND-ONLY.

The fleet audit (scripts/hoch_fleet_audit.py) proved ~45 hoch runtimes live and hand-flagged three
classes with competing loops. This tool goes one level deeper and does it from evidence instead of a
hardcoded list: for every hoch launchd job it resolves the plist, follows the entry script one level,
statically extracts the STATE FILES that job writes, and detects where two different jobs write the
SAME file. Same-file writers = a genuine competing loop (last-writer-wins races on brain state).

For each class that has contention it recommends ONE canonical owner and lists the others as bootout
candidates — but it NEVER stops anything. Stopping a runtime is a T3 action (operator approval). This
script has no code path that calls `launchctl bootout`/`unload`/`kill`/`remove`; every recommended
stop is emitted as an inert record tagged PENDING_OPERATOR_APPROVAL_T3, executed=false.

Honesty notes (no fake-green):
- The write-set extraction is a STATIC HEURISTIC (regex over script + one level of referenced
  scripts/modules). It can miss dynamically-computed paths. Findings are labeled "heuristic".
- launchctl + plist reading only work on the Mac. Off-Mac this prints an honest unavailable message
  and exits non-zero — it does not fabricate a fleet.
"""
from __future__ import annotations

import json
import os
import re
import plistlib
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prompt_brain" / "fleet_reconcile.json"

# Hard invariant: this module must never stop a runtime. These tokens are forbidden as executed ops.
NEVER_EXECUTE = True
_FORBIDDEN_OPS = ("bootout", "bootstrap", "unload", "remove", "kill", "disable")

# Where launchd plists live, most-specific first (repo copies are the source of truth for content).
PLIST_DIRS = [
    ROOT / "deploy" / "launchd",
    ROOT / "deploy" / "local-autonomy",
    ROOT,
    Path.home() / "Library" / "LaunchAgents",
    Path("/Library/LaunchAgents"),
    Path("/Library/LaunchDaemons"),
]

# Per-class canonical-owner preference (the consolidated "new" runtime the handoff wants to keep).
# First match wins; anything else in the class that shares a file is a bootout candidate.
CANONICAL_PREF = {
    "EXECUTOR/CADENCE": ["com.hoch.daemon"],
    "SWARM/SECURITY": ["com.hoch.agent.swarm.runtime", "com.hoch.live-swarm"],
    "AUDIT": ["com.hoch.daemon"],  # agent_audit + self_heal now run inside the daemon loop
}

# State-file write signals (repo-relative). Heuristic — the point is contention, not completeness.
_STATE_HINTS = (
    r"data/prompt_brain/[\w./-]+\.jsonl?",
    r"frontend/data/[\w./-]+\.json",
    r"data/backups/[\w./-]+",
)
_WRITE_CALLS = (r"write_text\s*\(", r"json\.dump\s*\(", r"open\s*\([^)]*['\"][wa]")


def _classify(label: str) -> str:
    """Functional class for a launchd label. Kept in sync with hoch_fleet_audit.CLASS."""
    table = [
        (r"\.mesh|mesh-broker", "MESH"),
        (r"\.family", "FAMILY (Pods)"),
        (r"live-swarm|cyber|\.swarm\.|swarm\.runtime", "SWARM/SECURITY"),
        (r"autonomous-audit|agent_audit|\.audit", "AUDIT"),
        (r"autonomous\.executor|autopulse|tool\.bridge|\.daemon|factory\.tick|cadence", "EXECUTOR/CADENCE"),
        (r"runtime|\.api|console|event\.server|pert-server|sidecar", "RUNTIME/API"),
        (r"tracker|actions\.runner|e2e|\.ci|burnin", "CI/TRACKER"),
        (r"memory", "MEMORY"),
        (r"health|watchdog|supervisor|gowatch|reconciler", "OPS/HEALTH"),
        (r"phase", "PHASE (build)"),
    ]
    for rx, c in table:
        if re.search(rx, label):
            return c
    return "OTHER"


def extract_output_paths(text: str) -> set[str]:
    """Statically pull repo-relative state-file paths a script/module appears to WRITE.

    Heuristic: a path matches a state-file hint AND the file mentions a write call somewhere. We do
    not try to bind a specific path to a specific write() — the goal is 'which jobs touch this file',
    for which co-occurrence is a sound, conservative signal.
    """
    if not any(re.search(w, text) for w in _WRITE_CALLS):
        return set()
    paths: set[str] = set()
    for hint in _STATE_HINTS:
        for m in re.findall(hint, text):
            paths.add(m.strip().strip("\"'"))
    return paths


def entry_scripts(program_arguments: list[str]) -> list[str]:
    """The real entrypoints from a plist ProgramArguments (drop interpreters like /bin/bash, python3)."""
    out = []
    for a in program_arguments or []:
        base = os.path.basename(a)
        if base in ("bash", "sh", "zsh", "python", "python3", "env", "-lc", "-c", "-l"):
            continue
        if a.startswith("-"):
            continue
        if a.endswith((".sh", ".py")) or "/scripts/" in a or "/backend/" in a:
            out.append(a)
    return out


def referenced_files(text: str) -> list[str]:
    """One level of fan-out: scripts a shell entrypoint calls, and python modules it runs."""
    refs = []
    for m in re.findall(r"(?:scripts|backend)/[\w./-]+\.(?:sh|py)", text):
        refs.append(m)
    for m in re.findall(r"python3?\s+-m\s+([\w.]+)", text):
        refs.append(m.replace(".", "/") + ".py")
    return refs


def collect_writes_for_job(program_arguments: list[str], read_text) -> set[str]:
    """Union of state files written by a job's entry scripts + one level of referenced files.

    `read_text(repo_relative_or_abs_path) -> str | None` is injected so this stays pure/testable and
    filesystem access is the caller's concern.
    """
    seen_files: set[str] = set()
    queue = list(entry_scripts(program_arguments))
    writes: set[str] = set()
    while queue:
        f = queue.pop()
        if f in seen_files:
            continue
        seen_files.add(f)
        txt = read_text(f)
        if not txt:
            continue
        writes |= extract_output_paths(txt)
        for r in referenced_files(txt):
            if r not in seen_files:
                queue.append(r)
    return writes


def detect_contention(job_writes: dict[str, set[str]]) -> dict[str, list[str]]:
    """Invert job->files into file->jobs, keeping only files written by 2+ distinct jobs."""
    by_file: dict[str, set[str]] = {}
    for label, files in job_writes.items():
        for f in files:
            by_file.setdefault(f, set()).add(label)
    return {f: sorted(js) for f, js in by_file.items() if len(js) > 1}


def _pick_owner(labels: list[str], cls: str) -> str:
    for pref in CANONICAL_PREF.get(cls, []):
        for lb in labels:
            if lb == pref or lb.startswith(pref):
                return lb
    return sorted(labels)[0]  # deterministic fallback; operator can override


def recommend(job_class: dict[str, str], contention: dict[str, list[str]]) -> dict:
    """Per class with contention, choose one owner and mark peers as T3 bootout candidates (inert)."""
    class_writers: dict[str, set[str]] = {}
    for _f, labels in contention.items():
        for lb in labels:
            class_writers.setdefault(job_class.get(lb, "OTHER"), set()).add(lb)

    recs, actions = [], []
    for cls, labels in sorted(class_writers.items()):
        labs = sorted(labels)
        if len(labs) < 2:
            continue
        owner = _pick_owner(labs, cls)
        losers = [lb for lb in labs if lb != owner]
        contested = sorted(f for f, w in contention.items() if set(w) & set(labs))
        recs.append({
            "class": cls,
            "canonical_owner": owner,
            "bootout_candidates": losers,
            "contested_files": contested,
            "reason": "Multiple runtimes in this class write the same state file(s) — "
                      "keep one writer to end last-writer-wins races.",
        })
        for lb in losers:
            actions.append({
                "op": "launchctl bootout  # DO NOT RUN AUTOMATICALLY",
                "target_label": lb,
                "keeps": owner,
                "tier": "T3",
                "status": "PENDING_OPERATOR_APPROVAL_T3",
                "executed": False,
            })
    return {"recommendations": recs, "actions": actions}


# ---- Mac-only I/O (guarded) -------------------------------------------------

def _live_hoch_jobs() -> list[dict]:
    raw = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=20).stdout
    jobs = []
    for line in raw.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, status, label = parts
        if "hoch" not in label.lower():
            continue
        jobs.append({"label": label, "pid": None if pid == "-" else pid, "status": status})
    return jobs


def _find_plist(label: str) -> Path | None:
    for d in PLIST_DIRS:
        cand = d / f"{label}.plist"
        if cand.exists():
            return cand
    # some repo plists are named by file not label; scan shallowly for a matching Label
    for d in PLIST_DIRS:
        if not d.exists():
            continue
        for p in d.glob("*.plist"):
            try:
                if plistlib.loads(p.read_bytes()).get("Label") == label:
                    return p
            except Exception:
                continue
    return None


def _repo_read_text(rel_or_abs: str) -> str | None:
    p = Path(rel_or_abs)
    for cand in ([p] if p.is_absolute() else [ROOT / p, ROOT / "scripts" / p, ROOT / p.name]):
        try:
            if cand.exists():
                return cand.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    return None


def reconcile() -> dict:
    try:
        jobs = _live_hoch_jobs()
    except Exception as e:
        return {"error": f"launchctl unavailable ({e}) — run this on the Mac (no fleet fabricated)."}

    job_class, job_writes, unresolved = {}, {}, []
    for j in jobs:
        label = j["label"]
        job_class[label] = _classify(label)
        plist = _find_plist(label)
        if not plist:
            unresolved.append(label)
            continue
        try:
            pa = plistlib.loads(plist.read_bytes()).get("ProgramArguments", [])
        except Exception:
            unresolved.append(label)
            continue
        job_writes[label] = collect_writes_for_job(pa, _repo_read_text)

    contention = detect_contention(job_writes)
    plan = recommend(job_class, contention)
    out = {
        "schema": "hoch-fleet-reconcile-v1",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "DRY-RUN — recommend only, nothing stopped",
        "method": "heuristic static write-set extraction (regex, 1-level fan-out)",
        "jobs_examined": len(jobs),
        "jobs_with_write_set": sum(1 for v in job_writes.values() if v),
        "unresolved_plists": sorted(unresolved),
        "contested_files": contention,
        **plan,
        "safety": {
            "never_executes": True,
            "all_actions_pending_operator_T3": all(
                a["executed"] is False and a["status"].endswith("T3") for a in plan["actions"]
            ),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main() -> int:
    r = reconcile()
    if "error" in r:
        print(r["error"])
        return 1
    print(f"HOCH RECONCILE (DRY-RUN) — {r['jobs_examined']} jobs examined, "
          f"{len(r['contested_files'])} contested state file(s)")
    if r["unresolved_plists"]:
        print(f"  unresolved plists (skipped, honest): {', '.join(r['unresolved_plists'])}")
    if not r["recommendations"]:
        print("  no same-file contention detected by the heuristic — nothing to reconcile.")
    for rec in r["recommendations"]:
        print(f"\n  [{rec['class']}] keep -> {rec['canonical_owner']}")
        print(f"    bootout candidates (T3, NOT run): {', '.join(rec['bootout_candidates'])}")
        for f in rec["contested_files"]:
            print(f"    contested: {f}")
    print(f"\n  {len(r['actions'])} stop action(s) staged as PENDING_OPERATOR_APPROVAL_T3 "
          f"(executed=false). Nothing was stopped.")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
