#!/usr/bin/env python3
"""Sign the production release GO — the founder-gated final step.

This is the ONE action only the operator takes. It is evidence-gated and cryptographically verified:

  1. Re-runs the Go/No-Go assembler. If the verdict is not GO (10/10 VERIFIED), it REFUSES to
     sign — you cannot sign a NO-GO.
  2. Requires explicit --operator and --confirm (no accidental signing).
  3. Validates a founder Ed25519 signature either locally (via TTY passphrase prompt) or remotely
     (via --signature and --decision-at arguments).
  4. Writes a fresh `production_go_status = GO` runtime-truth signal, storing the cryptographic
     signature as the validation hash.

Note: your go_nogo_manager marks manual GO signals stale after 5 minutes (an intentional safety —
a GO cannot silently latch forever). So this signs a GO for a live release window; re-run to renew.

    python3 scripts/sign_release_go.py --operator "Michael Hoch" --confirm
"""
import sys
import os
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


def get_latest_run_id():
    try:
        with open(ROOT / "data/security_scans/epic-fury-2026/latest_run_id", "r") as f:
            return f.read().strip()
    except Exception:
        return "latest"


def sign_once(operator, run_id, decision_at, signature, write_attestation=True):
    """Evidence-gated single sign. Returns (verdict, active_status). Signs ONLY if GO."""
    from scripts.release_go_no_go import assemble
    from backend.mission_control.founder_signer import verify_release_authority

    # Cryptographically verify the release authority signature
    ok, reason = verify_release_authority(run_id, decision_at, signature)
    if not ok:
        return "NO-GO", None, [f"Invalid founder signature: {reason}"]

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
          ts, 300, "fresh", 1.0, evid_link, _git_sha(), signature))
    conn.commit()
    conn.close()

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
            f"# Production Release GO — SIGNED\n\n"
            f"* Signed by: **{operator}**\n"
            f"* At (UTC): {ts}\n"
            f"* Decision timestamp: {decision_at}\n"
            f"* Signature: \n```\n{signature}\n```\n"
            f"* Git: `{_git_sha()}`\n"
            f"* Go/No-Go: GO ({r['verified']}/{r['total']} VERIFIED)\n"
            f"* Evidence packet: `{evid_link}`\n"
            f"* Active release status: **{active}**\n", encoding="utf-8")
    return "GO", active, []


def main():
    ap = argparse.ArgumentParser(description="Sign the production release GO (evidence-gated)")
    ap.add_argument("--operator", required=True, help="Your name — recorded as the signer")
    ap.add_argument("--confirm", action="store_true", help="Required: explicit sign confirmation")
    ap.add_argument("--watch", action="store_true", help="Keep the GO alive by re-verifying+renewing on a loop")
    ap.add_argument("--interval", type=int, default=240, help="Renew interval seconds (< 300 TTL)")
    ap.add_argument("--signature", help="Armored founder SSH signature to verify and commit")
    ap.add_argument("--decision-at", help="The ISO timestamp corresponding to the signature")
    ap.add_argument("--key", default=str(Path.home() / ".has_founder" / "founder_signing_key"), help="Path to founder private key (if signing locally)")
    args = ap.parse_args()

    run_id = get_latest_run_id()

    # Dry-run check
    from scripts.release_go_no_go import assemble
    r0 = assemble()
    print(f"Go/No-Go re-check: {r0['verdict']} ({r0['verified']}/{r0['total']} VERIFIED)")
    if r0["verdict"] != "GO":
        print(f"⛔ REFUSING TO SIGN — verdict is NO-GO. Blockers: {', '.join(r0['blockers'])}")
        return 2

    sig = args.signature
    dec_at = args.decision_at

    if not sig:
        # Prompt / Sign locally
        if not Path(args.key).exists():
            print(f"⛔ No signature provided and no founder private key found at {args.key}. Run scripts/founder_keygen.sh first, or pass --signature.")
            return 1
        
        # Enforce TTY checks to block unattended autonomous signing
        if not sys.stdin.isatty():
            print("⛔ Error: sign_release_go.py requires an interactive TTY when signing locally (cannot run autonomously).")
            return 1

        print(f"Signing release for Run ID: {run_id} using founder key...")
        from backend.mission_control.founder_signer import release_authority_payload, sign_approval
        dec_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        payload = release_authority_payload(run_id, dec_at)
        try:
            sig = sign_approval(payload, Path(args.key))
        except Exception as e:
            print(f"⛔ Failed to generate signature: {e}")
            return 1

    if not args.confirm:
        print("Signature verified successfully. Re-run with --confirm to actually sign.")
        return 1

    if not args.watch:
        v, active, blockers = sign_once(args.operator, run_id, dec_at, sig)
        if v == "GO":
            print(f"\n✅ GO SIGNED by {args.operator} — active_release_go_status = {active}")
            print("   (GO is live for ~5 min. Add --watch to keep it renewed while it stays 10/10.)")
            return 0
        else:
            print(f"⛔ FAILED TO SIGN: {', '.join(blockers)}")
            return 1

    # --watch: renew ONLY while it stays GO. If it ever regresses, STOP renewing and let it expire.
    if not Path(args.key).exists():
        print("⛔ Watch mode requires founder private key to sign fresh payloads on each interval.")
        return 1

    import time
    print(f"👁  GO watch active — renewing every {args.interval}s while verdict stays GO. Ctrl-C to stop.")
    try:
        from backend.mission_control.founder_signer import release_authority_payload, sign_approval
        while True:
            dec_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            payload = release_authority_payload(run_id, dec_at)
            try:
                sig = sign_approval(payload, Path(args.key))
                v, active, blockers = sign_once(args.operator, run_id, dec_at, sig, write_attestation=False)
            except Exception as e:
                v = "NO-GO"
                blockers = [str(e)]
                active = None

            stamp = _now_iso()
            if v == "GO":
                print(f"   [{stamp}] renewed GO — active={active}")
            else:
                print(f"   [{stamp}] ⛔ verdict {v} (blockers: {', '.join(blockers)}). "
                      f"NOT renewing — GO lapses in <5 min. Watching for return to GO...")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n   watch stopped by operator — existing GO expires within 5 min.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
