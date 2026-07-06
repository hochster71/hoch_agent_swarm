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
# Deck-readable mirror (the command deck's static fallback path serves frontend/data/*.json).
DECK_OUT = ROOT / "frontend" / "data" / "fleet_reconcile.json"

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


# Anchors: keep only the state-bearing tail of a reconstructed path (drop ROOT/var prefixes).
_PATH_ANCHORS = ("data/prompt_brain", "frontend/data", "data/backups", "data/")
# A pathlib chain like  ROOT / "data" / "prompt_brain" / "champion_registry.json"  or
# "frontend" / "data" / f"{name}.json"  — quoted segments joined by '/', ending in a json file.
_PATHLIB_CHAIN = re.compile(r'(?:["\']([\w.\-]+)["\']\s*/\s*){1,6}["\']([\w.\-]+\.jsonl?)["\']')


def _anchor(path: str) -> str:
    """Trim a reconstructed path to start at a known state anchor, so ROOT/var prefixes don't split
    the same file into two different keys across jobs."""
    for a in _PATH_ANCHORS:
        i = path.find(a)
        if i != -1:
            return path[i:]
    return path


def extract_output_paths(text: str) -> set[str]:
    """Statically pull repo-relative state-file paths a script/module appears to WRITE.

    Heuristic: a path matches a state-file hint AND the file mentions a write call somewhere. Catches
    BOTH literal slash-paths ("data/prompt_brain/x.json") AND pathlib chains
    (ROOT / "data" / "prompt_brain" / "x.json"), since HOCH code overwhelmingly uses the latter — a
    literal-only matcher would miss the real competing writers. We do not bind a path to a specific
    write(); co-occurrence of a state path + a write call is a sound, conservative 'this job touches
    this file' signal.
    """
    if not any(re.search(w, text) for w in _WRITE_CALLS):
        return set()
    paths: set[str] = set()
    for hint in _STATE_HINTS:                       # literal slash-paths
        for m in re.findall(hint, text):
            paths.add(_anchor(m.strip().strip("\"'")))
    for parts in re.finditer(_PATHLIB_CHAIN, text):  # pathlib joins
        segs = re.findall(r'["\']([\w.\-]+)["\']', parts.group(0))
        joined = _anchor("/".join(segs))
        if any(a in joined for a in _PATH_ANCHORS) or joined.endswith((".json", ".jsonl")):
            paths.add(joined)
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


_WRITE_LINE = re.compile(r"write_text|json\.dump|\.dump\(|open\([^)]*['\"][wa]|>>|(?<![0-9])>\s|save\(|to_json")


def evidence_for_path(program_arguments: list[str], read_text, target: str) -> list[dict]:
    """For a contested path, return every line in a job's reachable scripts that mentions it, tagged
    WRITE vs read/ref. Turns the conservative co-write flag into inspectable evidence so the operator
    can tell a real race from a read-one/write-other pair before approving a T3 stop."""
    base = target.rstrip("/").split("/")[-1]
    seen: set[str] = set()
    queue = list(entry_scripts(program_arguments))
    hits: list[dict] = []
    while queue:
        f = queue.pop()
        if f in seen:
            continue
        seen.add(f)
        txt = read_text(f)
        if not txt:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            if base in line:
                kind = "WRITE" if _WRITE_LINE.search(line) else "read/ref"
                hits.append({"file": f, "line": i, "kind": kind, "text": line.strip()[:140]})
        for r in referenced_files(txt):
            if r not in seen:
                queue.append(r)
    return hits


def detect_contention(job_writes: dict[str, set[str]]) -> dict[str, list[str]]:
    """Invert job->files into file->jobs, keeping only files written by 2+ distinct jobs."""
    by_file: dict[str, set[str]] = {}
    for label, files in job_writes.items():
        for f in files:
            by_file.setdefault(f, set()).add(label)
    return {f: sorted(js) for f, js in by_file.items() if len(js) > 1}


def _pick_owner(labels: list[str], job_class: dict[str, str]) -> str:
    """Choose the one writer allowed to keep writing a contested file. Prefers a class-canonical
    runtime (CANONICAL_PREF) among the writers — checked across EACH writer's own class, so it works
    even when the competing writers span different classes. Deterministic fallback: sorted-first."""
    best, best_rank = None, 1 << 30
    for lb in sorted(labels):
        prefs = CANONICAL_PREF.get(job_class.get(lb, "OTHER"), [])
        rank = next((i for i, p in enumerate(prefs) if lb == p or lb.startswith(p)), 1 << 29)
        if rank < best_rank:
            best, best_rank = lb, rank
    return best if best is not None else sorted(labels)[0]


def recommend(job_class: dict[str, str], contention: dict[str, list[str]]) -> dict:
    """Recommend ONE canonical owner PER CONTESTED FILE (not per class) and mark the other writers as
    T3 bootout candidates (inert). Per-file is the correct unit: two runtimes racing on the same state
    file are a competing loop even when they belong to different functional classes — the earlier
    per-class grouping silently missed exactly that (e.g. an OPS/HEALTH job and a PHASE job both
    writing tasks/phase50_tasks.json)."""
    recs, actions = [], []
    for f, writers in sorted(contention.items()):
        w = sorted(writers)
        owner = _pick_owner(w, job_class)
        losers = [lb for lb in w if lb != owner]
        recs.append({
            "contested_file": f,
            "contested_files": [f],                       # array kept for the deck panel's renderer
            "writers": w,
            "writer_classes": {lb: job_class.get(lb, "OTHER") for lb in w},
            "class": job_class.get(owner, "OTHER"),
            "canonical_owner": owner,
            "bootout_candidates": losers,
            "reason": f"{len(w)} runtimes write {f} — keep one writer to end last-writer-wins races.",
        })
        for lb in losers:
            actions.append({
                "op": "launchctl bootout  # DO NOT RUN AUTOMATICALLY",
                "target_label": lb,
                "keeps": owner,
                "contested_file": f,
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


def _jobs_from_audit(audit_path: Path) -> tuple[list[dict], str]:
    """Use the launchctl snapshot the audit already captured live on the Mac as the job list.
    Lets the reconciler run off-Mac against REAL fleet data (labels are real; only plists that live in
    the repo resolve to write-sets — the rest are reported honestly as unresolved)."""
    a = json.loads(audit_path.read_text())
    jobs = [{"label": r["label"]} for r in (a.get("running", []) + a.get("loaded", []))]
    return jobs, f"fleet_audit.json snapshot captured live on Mac at {a.get('at', '?')}"


def reconcile(source_jobs: list[dict] | None = None, source_note: str = "live launchctl") -> dict:
    if source_jobs is not None:
        jobs = source_jobs
    else:
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
        "job_source": source_note,
        "method": "heuristic static write-set extraction (regex, transitive fan-out; literal + pathlib paths)",
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
    payload = json.dumps(out, indent=2)
    OUT.write_text(payload, encoding="utf-8")
    try:
        DECK_OUT.parent.mkdir(parents=True, exist_ok=True)
        DECK_OUT.write_text(payload, encoding="utf-8")  # deck reads this via /data/ static fallback
    except Exception:
        pass  # deck mirror is best-effort; the canonical write above already succeeded
    return out


def explain(target: str) -> int:
    """Show, per writer of a contested file, the exact file+line evidence (WRITE vs read/ref) so the
    operator can judge a real race before approving a T3 stop. Reads the prior reconcile output for the
    writer list, then re-resolves each writer's scripts on disk."""
    if not OUT.exists():
        print(f"no {OUT.relative_to(ROOT)} — run the reconciler first.")
        return 1
    prior = json.loads(OUT.read_text())
    writers = prior.get("contested_files", {}).get(target)
    if not writers:
        print(f"'{target}' is not in the current contested set. Contested files: "
              f"{', '.join(prior.get('contested_files', {})) or '(none)'}")
        return 1
    print(f"EVIDENCE for {target} (WRITE = matched a write-call on the same line):")
    for lb in writers:
        plist = _find_plist(lb)
        if not plist:
            print(f"\n  {lb}: plist unresolved"); continue
        try:
            pa = plistlib.loads(plist.read_bytes()).get("ProgramArguments", [])
        except Exception:
            print(f"\n  {lb}: plist unreadable"); continue
        ev = evidence_for_path(pa, _repo_read_text, target)
        writes = [h for h in ev if h["kind"] == "WRITE"]
        print(f"\n  {lb}  — {len(writes)} WRITE line(s), {len(ev)-len(writes)} read/ref")
        for h in ev[:8]:
            print(f"    [{h['kind']:8}] {h['file']}:{h['line']}  {h['text']}")
    print("\n  If exactly one writer shows WRITE lines, the other only reads — likely NOT a race; keep\n"
          "  the writer. If both WRITE, it's a real last-writer-wins race — keep one, stop the other (T3).")
    return 0


def main() -> int:
    import sys
    if "--explain" in sys.argv:
        i = sys.argv.index("--explain")
        tgt = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        if not tgt:
            print("usage: --explain <contested/file/path.json>"); return 1
        return explain(tgt)
    if "--from-audit" in sys.argv:
        ap = ROOT / "data" / "prompt_brain" / "fleet_audit.json"
        if not ap.exists():
            print(f"no {ap.relative_to(ROOT)} — run scripts/hoch_fleet_audit.py on the Mac first.")
            return 1
        jobs, note = _jobs_from_audit(ap)
        r = reconcile(source_jobs=jobs, source_note=note)
    else:
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
        print("\n  contested: " + rec["contested_file"])
        wc = rec.get("writer_classes", {})
        writers = ", ".join("{} [{}]".format(w, wc.get(w, "?")) for w in rec["writers"])
        print("    writers: " + writers)
        print("    keep -> " + rec["canonical_owner"])
        print("    bootout candidates (T3, NOT run): " + ", ".join(rec["bootout_candidates"]))
    print(f"\n  {len(r['actions'])} stop action(s) staged as PENDING_OPERATOR_APPROVAL_T3 "
          f"(executed=false). Nothing was stopped.")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
