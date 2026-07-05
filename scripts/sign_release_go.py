#!/usr/bin/env python3
"""Sign the production release GO — the founder-gated final step.

This is the ONE action only the operator takes. It is evidence-gated and cannot fake-green:

  1. Re-runs the Go/No-Go assembler. If the verdict is not GO (10/10 VERIFIED), it REFUSES to
     sign — you cannot sign a NO-GO.
  2. Requires explicit --operator and --confirm (no accidental signing).
  3. Writes a fresh `production_go_status = GO` runtime-truth signal attributed to you, linked to
     the Go/No-Go evidence packet, then recomputes the release status.

Note: your go_nogo_manager marks manual GO signals stale after 5 minutes (an intentional safety —
a GO cannot silently latch forever). So this signs a GO for a live release window; re-run to renew.

    python3 scripts/sign_release_go.py --operator "Michael Hoch" --confirm
"""
import sys
import json
import argparse
import datetime
import subprocess
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.runtime_truth.state_store import DB_PATH  # noqa: E402


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser(description="Sign the production release GO (evidence-gated)")
    ap.add_argument("--operator", required=True, help="Your name — recorded as the signer")
    ap.add_argument("--confirm", action="store_true", help="Required: explicit sign confirmation")
    args = ap.parse_args()

    # 1. Evidence gate — re-verify GO. Refuse to sign a NO-GO.
    from scripts.release_go_no_go import assemble  # local import
    r = assemble()
    print(f"Go/No-Go re-check: {r['verdict']} ({r['verified']}/{r['total']} VERIFIED)")
    if r["verdict"] != "GO":
        print(f"⛔ REFUSING TO SIGN — verdict is NO-GO. Blockers: {', '.join(r['blockers'])}")
        return 2
    if not args.confirm:
        print("Verdict is GO. Re-run with --confirm to actually sign.")
        return 1

    # 2. Write the operator-attributed, evidence-linked GO signal.
    evid = sorted((ROOT / "docs/evidence/release").glob("GO_NO_GO_*.md"))
    evid_link = str(evid[-1].relative_to(ROOT)) if evid else ""
    ts = _now_iso()
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, ("production_go_status", "Production Release GO", "GO", args.operator, "operator",
          ts, 300, "fresh", 1.0, evid_link, _git_sha(), ""))
    conn.commit(); conn.close()

    # 3. Recompute release status.
    try:
        from backend.runtime_truth.go_nogo_manager import GoNoGoManager
        summary = GoNoGoManager(db_path=str(DB_PATH)).process_and_update()
        active = summary.get("release_go_status") or summary.get("active_release_go_status")
    except Exception as e:
        active = f"(recompute error: {e})"

    # 4. Attestation.
    att = ROOT / "docs/evidence/release" / f"GO_SIGNED_{ts.replace(':','').replace('-','')}.md"
    att.parent.mkdir(parents=True, exist_ok=True)
    att.write_text(
        f"# Production Release GO — SIGNED\n\n"
        f"* Signed by: **{args.operator}**\n* At (UTC): {ts}\n* Git: `{_git_sha()}`\n"
        f"* Go/No-Go: {r['verdict']} ({r['verified']}/{r['total']} VERIFIED)\n"
        f"* Evidence packet: `{evid_link}`\n* Active release status: **{active}**\n\n"
        f"Signal `production_go_status=GO` written (ttl 300s — renew to keep the window open).\n",
        encoding="utf-8")

    print(f"\n✅ GO SIGNED by {args.operator} at {ts}")
    print(f"   active_release_go_status = {active}")
    print(f"   attestation = {att}")
    print("   (GO is live for ~5 min; readiness will reflect it while fresh. Re-run to renew.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
