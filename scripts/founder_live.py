#!/usr/bin/env python3
"""founder_live.py — the HELM Founder Live board.

Two panels, two kinds of truth, deliberately not blended:

    LIVE STATE  <- collectors.py   what the machine IS, re-read every render
    RECENT WORK <- envelopes       what missions DID, written once at close

Invariants:
  * Status is re-derived here from recorded facts. A stored or forged status field in
    an envelope is ignored.
  * A collector Reading past its freshness SLA is CACHED (non-advancing) regardless of
    what its payload claims. A six-day-old "HEALTHY" renders STALE, never green.
  * A domain with no collector renders NO COLLECTOR. Silence stays loud.
  * Every scalar traces to a Reading or an envelope field. Untraceable numbers cannot
    reach this board.

Usage:
    python3 scripts/founder_live.py              # full board (runs the test suite)
    python3 scripts/founder_live.py --fast       # skip test execution
    python3 scripts/founder_live.py --json       # machine-readable
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.collectors import (  # noqa: E402
    SCOPE_INDIRECT, SCOPE_LOCAL, SCOPE_REMOTE, collect_all, domain_verdict,
)
from backend.helm_runtime.mission_envelope import (  # noqa: E402
    STATUS_DEGRADED, STATUS_FAILED, STATUS_PARTIAL, STATUS_PENDING_EVIDENCE,
    STATUS_RUNNING, STATUS_VERIFIED, load_envelopes,
)

W = 78

GLYPH = {
    STATUS_VERIFIED: "✓", STATUS_PENDING_EVIDENCE: "✓", STATUS_PARTIAL: "!",
    STATUS_DEGRADED: "!", STATUS_FAILED: "✗", STATUS_RUNNING: "▸",
}

VERDICT_GLYPH = {
    "OBSERVED": "●", "STALE": "◐", "UNREACHABLE": "○", "NO_COLLECTOR": "○",
}

DOMAINS_ORDER = [
    "engineering", "qualification", "deployment", "factory",
    "family_ops", "calendar_ops", "home_ops", "finance_ops",
    "research", "founder_decision",
]


def _rederive(env: dict) -> str:
    """Recompute envelope status from facts. A stored status is never trusted."""
    if not env.get("completed_at"):
        return STATUS_RUNNING
    errors = env.get("errors") or []
    unknowns = env.get("unknowns") or []
    evidence = env.get("evidence") or []
    mutations = [m for m in (env.get("mutations") or []) if m.get("kind") != "none"]
    produced = bool(evidence) or bool(mutations)
    if [e for e in errors if e.get("severity") == "RED"] and not produced:
        return STATUS_FAILED
    if errors:
        return STATUS_DEGRADED
    if unknowns:
        return STATUS_PARTIAL
    sources = env.get("sources") or []
    if any(s.get("truth") not in ("OBSERVED", "DERIVED") for s in sources):
        return STATUS_PARTIAL
    if any(not s.get("evidence") for s in sources) or not evidence:
        return STATUS_PENDING_EVIDENCE
    return STATUS_VERIFIED


def _line(s: str = "") -> str:
    return "║ " + s.ljust(W - 4)[: W - 4] + " ║"


def _rule(l: str, m: str, r: str) -> str:
    return l + m * (W - 2) + r


def render(readings: list, envelopes: list) -> str:
    out: list = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    for e in envelopes:
        e["_status"] = _rederive(e)

    by_name = {r.name: r for r in readings}
    verdicts = {d: domain_verdict(readings, d) for d in DOMAINS_ORDER}
    live_domains = [d for d, v in verdicts.items() if v == "OBSERVED"]
    stale = [r for r in readings if r.truth.value == "CACHED"]
    unreachable = [r for r in readings if r.truth.value == "UNKNOWN"]

    out.append(_rule("╔", "═", "╗"))
    out.append(_line("HELM • FOUNDER LIVE"))
    out.append(_rule("╠", "═", "╣"))
    out.append(_line(f"AS OF {now}   collectors: {len(readings)}   "
                     f"live domains: {len(live_domains)}/{len(DOMAINS_ORDER)}"))
    out.append(_line(f"STALE SIGNALS: {len(stale)}   UNREACHABLE: {len(unreachable)}   "
                     f"envelopes: {len(envelopes)}"))

    # ---- LIVE STATE ----------------------------------------------------------
    out.append(_rule("╠", "═", "╣"))
    out.append(_line("LIVE STATE   (re-read this render; freshness gates truth)"))
    out.append(_line())

    g = by_name.get("git")
    if g and g.advancing:
        v = g.value
        out.append(_line(f"  GIT      HEAD {v['head']}   branch {v['branch']}"))
        out.append(_line(f"           tree {v['tree']}   worktree {v['worktree']}"))
        out.append(_line(f"           last commit {v['last_commit_age']} ago: {v['last_commit']}"))
    else:
        out.append(_line(f"  GIT      UNAVAILABLE — {g.error if g else 'no collector'}"))
    out.append(_line())

    t = by_name.get("tests")
    if t and t.advancing:
        v = t.value
        out.append(_line(f"  TESTS    {v['verdict']}   passed {v['passed']}   "
                         f"failed {v['failed']}   errors {v['errors']}"))
        out.append(_line(f"           target {v['target']}   {v['duration_s']}s   "
                         f"(executed this render)"))
    else:
        out.append(_line(f"  TESTS    NOT OBSERVED — {t.error if t else 'no collector'}"))
    out.append(_line())

    p = by_name.get("processes")
    if p and p.advancing:
        out.append(_line(f"  PROCESS  host {p.value.get('host')}   "
                         f"{p.value.get('count')} processes"))
    else:
        out.append(_line("  PROCESS  NOT OBSERVABLE FROM THIS HOST"))
        if p and p.error:
            for chunk in _wrap(p.error, W - 15):
                out.append(_line(f"           {chunk}"))
    out.append(_line())

    m = by_name.get("models")
    if m:
        out.append(_line("  MODELS   role bindings readable; per-model invocation state:"))
        out.append(_line(f"           {m.value.get('invocation_state', 'UNKNOWN')} "
                         f"— no runtime surface exposes it"))
    out.append(_line())

    # Hosts
    hosts = [r for r in readings if r.name.startswith("host:")]
    if hosts:
        out.append(_line("  HOSTS"))
        for r in hosts:
            mark = "LIVE " if r.advancing else ("STALE" if r.truth.value == "CACHED" else "UNK  ")
            tag = " (HELM runtime host)" if r.value.get("is_helm_runtime_host") else ""
            out.append(_line(f"    {mark} {r.value.get('host','?'):<26} "
                             f"last beat {r.age_human} ago{tag}"))
        out.append(_line())

    # Daemons / loops
    out.append(_line("  DAEMONS & LOOPS   (INDIRECT — files another host wrote)"))
    for nm in ("helm_supervisor", "ag_daemon", "council_loop", "qa_sentinel",
               "telemetry_freshness"):
        r = by_name.get(nm)
        if not r:
            continue
        if r.truth.value == "UNKNOWN":
            out.append(_line(f"    UNK   {nm:<20} {r.error or 'unreadable'}"))
            continue
        claimed = (r.value.get("declared_status") or r.value.get("declared_health")
                   or r.value.get("heartbeat_status") or r.value.get("status") or "-")
        mark = "LIVE " if r.advancing else "STALE"
        out.append(_line(f"    {mark} {nm:<20} claims '{claimed}' · "
                         f"written {r.age_human} ago (SLA {r.sla_seconds//60}m)"))
    out.append(_line())

    # ---- DOMAIN COVERAGE -----------------------------------------------------
    out.append(_rule("╠", "═", "╣"))
    out.append(_line("DOMAIN COVERAGE   ● observed  ◐ stale  ○ no collector / unreachable"))
    out.append(_line())
    for d in DOMAINS_ORDER:
        v = verdicts[d]
        note = {
            "OBSERVED": "live collector reporting",
            "STALE": "collector found data past its freshness SLA",
            "UNREACHABLE": "collector exists but cannot see its target",
            "NO_COLLECTOR": "NOT CONNECTED — status genuinely unknown",
        }[v]
        out.append(_line(f"  {VERDICT_GLYPH[v]} {d:<18} {v:<14} {note}"))
    out.append(_line())

    # ---- RECENT WORK ---------------------------------------------------------
    out.append(_rule("╠", "═", "╣"))
    out.append(_line("RECENT WORK   (mission envelopes — history, not liveness)"))
    out.append(_line())
    if not envelopes:
        out.append(_line("  (no envelopes emitted)"))
    for e in envelopes:
        st = e["_status"]
        out.append(_line(f"{GLYPH.get(st,'?')} {e.get('mission_id','?')}".ljust(52) + st))
        srcs = e.get("sources") or []
        ok = len([s for s in srcs if s.get("truth") in ("OBSERVED", "DERIVED")])
        muts = [x for x in (e.get("mutations") or []) if x.get("kind") != "none"]
        out.append(_line(f"  {e.get('title','')}  [{e.get('domain','?')}]"))
        out.append(_line(f"  sources {len(srcs)} ({ok} verified) · unknown "
                         f"{len(e.get('unknowns') or [])} · mutations {len(muts)}"))
        for u in (e.get("unknowns") or []):
            out.append(_line(f"    UNKNOWN  {u.get('subject')}: {u.get('reason')}"))
    out.append(_line())

    # ---- FOUNDER QUEUE -------------------------------------------------------
    out.append(_rule("╠", "═", "╣"))
    out.append(_line("FOUNDER QUEUE"))
    out.append(_line())
    gates = [e for e in envelopes if e.get("founder_action")]
    if not gates:
        out.append(_line("  (empty)"))
    for e in gates:
        fa = e["founder_action"]
        out.append(_line(f"  ◆ {fa.get('title','')}"))
        out.append(_line(f"    {fa.get('reason','')}"))
    out.append(_line())

    # ---- SYSTEM ISSUES -------------------------------------------------------
    out.append(_rule("╠", "═", "╣"))
    out.append(_line("SYSTEM ISSUES"))
    out.append(_line())
    if stale:
        out.append(_line("  STALE — signal exists but is past its freshness SLA:"))
        for r in sorted(stale, key=lambda x: -(x.age_seconds or 0)):
            out.append(_line(f"    AMBER  {r.name:<22} {r.age_human} old "
                             f"(SLA {r.sla_seconds//60}m) — treat as UNKNOWN"))
    if unreachable:
        out.append(_line("  UNREACHABLE — collector could not observe its target:"))
        for r in unreachable:
            out.append(_line(f"    AMBER  {r.name:<22} {(r.error or '')[:40]}"))
    for e in envelopes:
        for i in (e.get("errors") or []):
            out.append(_line(f"    {i.get('severity','AMBER'):<6} {i.get('subject')}: "
                             f"{i.get('detail')}"))
    if not (stale or unreachable):
        out.append(_line("  (none)"))
    out.append(_line())
    out.append(_rule("╚", "═", "╝"))
    return "\n".join(out)


def _wrap(s: str, width: int) -> list:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def main() -> int:
    fast = "--fast" in sys.argv
    readings = collect_all(run_tests=not fast)
    envelopes = load_envelopes()
    if "--json" in sys.argv:
        import json
        for e in envelopes:
            e["status_rederived"] = _rederive(e)
        print(json.dumps({
            "live_state": [r.to_dict() for r in readings],
            "envelopes": envelopes,
            "domain_verdicts": {d: domain_verdict(readings, d) for d in DOMAINS_ORDER},
        }, indent=2, default=str))
        return 0
    print(render(readings, envelopes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
