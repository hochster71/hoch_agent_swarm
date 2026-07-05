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


def sign_once(operator, write_attestation=True):
    """Evidence-gated single sign. Returns (verdict, active_status). Signs ONLY if GO."""
    from scripts.release_go_no_go import assemble
    r = assemble()
    if r["verdict"] != "GO":
        return r["verdict"], None, r["blockers"]
    evid = sorted((ROOT / "docs/evidence/release").glob("GO_NO_GO_*.md"))
    evid_link = str(evid[-1].relative_to(ROOT)) if evid else ""
    ts = _now_iso()
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, ("production_go_status", "Production Release GO", "GO", operator, "operator",
          ts, 300, "fresh", 1.0, evid_link, _git_sha(), ""))
    conn.commit(); conn.close()
    try:
        from backend.runtime_truth.go_nogo_manager import GoNoGoManager
        summary = GoNoGoManager(db_path=str(DB_PATH)).process_and_update()
        active = summary.get("release_go_status") or summary.get("active_release_go_status")
    except Exception as e:
        active = f"(recompute error: {e})"
    if write_attestation:
        att = ROOT / "docs/evidence/release" / f"GO_SIGNED_{ts.replace(':','').replace('-','')}.md"
        att.parent.mkdir(parents=True, exist_ok=True)
        att.write_text(
            f"# Production Release GO — SIGNED\n\n* Signed by: **{operator}**\n* At (UTC): {ts}\n"
            f"* Git: `{_git_sha()}`\n* Go/No-Go: GO ({r['verified']}/{r['total']} VERIFIED)\n"
            f"* Evidence packet: `{evid_link}`\n* Active release status: **{active}**\n", encoding="utf-8")
    return "GO", active, []


def main():
    ap = argparse.ArgumentParser(description="Sign the production release GO (evidence-gated)")
    ap.add_argument("--operator", required=True, help="Your name — recorded as the signer")
    ap.add_argument("--confirm", action="store_true", help="Required: explicit sign confirmation")
    ap.add_argument("--watch", action="store_true", help="Keep the GO alive by re-verifying+renewing on a loop")
    ap.add_argument("--interval", type=int, default=240, help="Renew interval seconds (< 300 TTL)")
    args = ap.parse_args()

    # Dry-run check
    from scripts.release_go_no_go import assemble
    r0 = assemble()
    print(f"Go/No-Go re-check: {r0['verdict']} ({r0['verified']}/{r0['total']} VERIFIED)")
    if r0["verdict"] != "GO":
        print(f"⛔ REFUSING TO SIGN — verdict is NO-GO. Blockers: {', '.join(r0['blockers'])}")
        return 2
    if not args.confirm:
        print("Verdict is GO. Re-run with --confirm to actually sign.")
        return 1

    if not args.watch:
        v, active, _ = sign_once(args.operator)
        print(f"\n✅ GO SIGNED by {args.operator} — active_release_go_status = {active}")
        print("   (GO is live for ~5 min. Add --watch to keep it renewed while it stays 10/10.)")
        return 0

    # --watch: renew ONLY while it stays GO. If it ever regresses, STOP renewing and let it expire.
    import time
    print(f"👁  GO watch active — renewing every {args.interval}s while verdict stays GO. Ctrl-C to stop.")
    try:
        while True:
            v, active, blockers = sign_once(args.operator, write_attestation=False)
            stamp = _now_iso()
            if v == "GO":
                print(f"   [{stamp}] renewed GO — active={active}")
            else:
                print(f"   [{stamp}] ⛔ verdict regressed to {v} (blockers: {', '.join(blockers)}). "
                      f"NOT renewing — GO will expire in <5 min. Watch stopping.")
                return 3
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n   watch stopped by operator — existing GO expires within 5 min.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
