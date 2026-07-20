#!/usr/bin/env python3
"""Emit the mission envelope for TECH-SCOUT-20260720.

This is a BACKFILL of the one mission this Builder session actually executed and can
attest to from artifacts on disk. It is deliberately narrow.

The family-ops, calendar-ops and home-ops runs described in the founder's 2026-07-20
message were executed by OTHER scheduled sessions. This Builder did not run them, cannot
re-read their intermediate state, and will not manufacture envelopes for them. Doing so
would reproduce the exact failure being corrected: numbers appearing on a founder board
with no artifact behind them. Those domains are represented on the board as UNATTESTED
until their own runs emit envelopes.

Every source below is verified by re-reading the artifact at run time. Nothing is
declared. If an artifact is missing, the source is recorded UNKNOWN and the derived
status drops accordingly — including for this script's own claims.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.mission_contract import Truth  # noqa: E402
from backend.helm_runtime.mission_envelope import MissionEnvelope  # noqa: E402

DIGEST = "docs/scout/tech-scout-2026-07-20.md"
TRACKER = "has_live_project_tracker/data/doorstep_digest.json"


def main() -> int:
    env = MissionEnvelope(
        "TECH-SCOUT-20260720",
        "research",
        agent="claude:builder",
        title="Weekly HAS tech scout",
    )

    env.step("PRIMARY_SOURCES_QUERIED")
    env.act("WebSearch sweep", "8 queries across changelogs, GitHub, dev blogs")

    # Sources that returned. TRUTH: these are ASSERTED, not OBSERVED — a web search
    # result read once in-session leaves no re-readable artifact. Being honest about
    # this is what keeps the mission out of the green band.
    for name in (
        "anthropic_changelog", "github_trending", "stripe_sessions_2026",
        "harness_engineering_repos", "appstore_mcp_repos",
    ):
        env.source(name, Truth.ASSERTED, detail="web search result; no cached artifact")

    # Sources that failed. These are the whole point.
    env.step("COMMUNITY_SOURCES_FAILED")
    env.unknown("hacker_news", "WebSearch returned 'unavailable'", attempted=1)
    env.unknown("reddit_r_ClaudeAI", "WebSearch returned 'unavailable'", attempted=1)
    env.unknown("x_twitter_dev_chatter", "not attempted after two connector failures")
    env.error("research_connectors", "HN and Reddit unreachable; coverage PARTIAL")

    # Outputs — verified by re-reading, not by claiming.
    env.step("DIGEST_GENERATED")
    digest = ROOT / DIGEST
    if digest.exists() and digest.stat().st_size > 0:
        env.mutate(DIGEST, "created", detail=f"{digest.stat().st_size} bytes", undo="git")
        env.prove(DIGEST)
        env.source("digest_file", Truth.OBSERVED, detail="re-read from disk", evidence=DIGEST)
    else:
        env.unknown("digest_file", "expected artifact absent at verification time")

    env.step("TRACKER_UPDATED")
    tracker = ROOT / TRACKER
    try:
        data = json.loads(tracker.read_text(encoding="utf-8"))
        if "tech_scout" in data:
            env.mutate(TRACKER, "updated", detail="added tech_scout key", undo="git")
            env.prove(TRACKER)
            env.source("tracker_file", Truth.OBSERVED,
                       detail=f"tech_scout key present; {len(data)} keys intact",
                       evidence=TRACKER)
        else:
            env.unknown("tracker_file", "tech_scout key absent after declared write")
    except Exception as exc:
        env.error("tracker_file", f"unreadable: {exc}")

    env.founder_gate(
        "Review Harness Evolver / Harness Forge",
        "modifies agent scaffolding; requires a defensible score model before adoption",
    )

    env.close()
    path = env.write()
    try:
        env.publish()
        published = "yes"
    except Exception as exc:
        published = f"no ({exc})"

    print(f"envelope: {path}")
    print(f"derived status: {env.status}")
    print(f"sources: {env.source_summary}")
    print(f"event bus: {published}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
