#!/usr/bin/env bash
# =============================================================================
# sign_r2_security.sh — founder signs the Epic Fury R2 security gate.
# =============================================================================
# DOORSTEP founder action, performed BY the founder. It:
#   1. shows you the gate verdict + the single finding,
#   2. requires you to type your name AND the word APPROVE (nothing is auto-signed),
#   3. stamps the sign-off block in the scan-results doc,
#   4. writes a RELEASE_APPROVAL evidence record (with the doc's sha256),
#   5. marks the 'r2-security-signoff' item SIGNED in the founder handoff queue.
# It does NOT change the DOORSTEP control plane (execution_posture stays DOORSTEP,
# provider/founder-gated execution stay OFF) — signing the gate is not the same as
# turning the swarm loose. App Store submission remains a separate founder gate.
# Run:  bash scripts/sign_r2_security.sh
# =============================================================================
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1

DOC="docs/evidence/products/epic-fury-2026/security_scan_results_20260707.md"
QUEUE="has_live_project_tracker/data/founder_handoff_queue.json"
[ -f "$DOC" ] || { echo "✗ scan-results doc not found: $DOC"; exit 1; }

echo "======================================================================"
echo " EPIC FURY R2 — SECURITY GATE SIGN-OFF"
echo "======================================================================"
echo
echo "---- Gate verdict (from $DOC) ----"
sed -n '/## Gate Verdict/,/## Founder Sign-off/p' "$DOC" | sed '/## Founder Sign-off/d'
echo "---- The single finding ----"
echo "  Apple Distribution code-signing cert (Team K34GR8P326)"
echo "  Disposition: ACCEPTED_FALSE_POSITIVE — not a service credential; version-controlled per Apple/Fastlane."
echo

# already signed?
if grep -q '\[x\] APPROVED' "$DOC"; then
  echo "ℹ This gate is already signed:"
  grep -E '\*\*(Signature|Date)\*\*' "$DOC" | sed 's/^/   /'
  exit 0
fi

echo "By signing you attest: you reviewed the scan, accept the false positive, and approve the gate."
printf "Type your FULL NAME to sign (or press Enter to cancel): "
read -r NAME
[ -z "$NAME" ] && { echo "cancelled — nothing signed."; exit 0; }
printf "Type APPROVE (all caps) to confirm, or anything else to cancel: "
read -r CONFIRM
[ "$CONFIRM" != "APPROVE" ] && { echo "not confirmed — nothing signed."; exit 0; }

NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATE_UTC="$(date -u +%Y-%m-%d)"

python3 - "$DOC" "$QUEUE" "$NAME" "$NOW_UTC" "$DATE_UTC" <<'PY'
import sys, json, hashlib, datetime, pathlib
doc, queue, name, now_utc, date_utc = sys.argv[1:6]
p = pathlib.Path(doc)
t = p.read_text(encoding="utf-8")

# stamp the sign-off block (tolerant of trailing spaces)
t = t.replace("[ ] APPROVED", "[x] APPROVED", 1)
import re
t = re.sub(r"\*\*Signature:\*\*\s*_+",
           f"**Signature:** {name} (typed electronic signature)", t, count=1)
t = re.sub(r"\*\*Date:\*\*\s*_+",
           f"**Date:** {date_utc}", t, count=1)
p.write_text(t, encoding="utf-8")
sha = hashlib.sha256(t.encode("utf-8")).hexdigest()

# evidence record
ev = pathlib.Path(f"docs/evidence/products/epic-fury-2026/RELEASE_APPROVAL_{now_utc.replace(':','').replace('-','')}.json")
ev.write_text(json.dumps({
    "artifact": "R2 security gate founder sign-off",
    "reviewer": name, "role": "Founder, sole approver",
    "decision": "APPROVED", "signed_at_utc": now_utc,
    "signed_doc": doc, "signed_doc_sha256": sha,
    "gate_verdict": {"R1_REAL_TOOLS":"PASS","R2_RECONCILED_SCAN":"PASS",
                     "R3_NO_OPEN_HIGH":"PASS","R5_POSTURE":"READY"},
    "note": "Security gate signed. DOORSTEP posture unchanged. App Store submission is a separate founder gate.",
}, indent=2), encoding="utf-8")

# mark the door item signed
try:
    q = json.load(open(queue))
    for it in q.get("staged", []):
        if it.get("id") == "r2-security-signoff":
            it["status"] = "SIGNED"; it["signed_by"] = name; it["signed_at"] = now_utc
            it["evidence"] = str(ev)
    json.dump(q, open(queue, "w"), indent=2)
except Exception as e:
    print(f"  (warn: could not update handoff queue: {e})")

print(f"✅ signed by {name} at {now_utc}")
print(f"   doc stamped : {doc}")
print(f"   evidence    : {ev}")
print(f"   doc sha256  : {sha[:16]}…")
PY

echo
echo "Next founder gate (still at the door): r2-appstore-submit — archive+upload the signed"
echo "build to App Store Connect (Team K34GR8P326). See docs/generated/r2/testflight_checklist.md."
echo
echo "Tip: commit the signature to lock it into the audit trail:"
echo "  git add $DOC docs/evidence/products/epic-fury-2026/RELEASE_APPROVAL_*.json $QUEUE"
echo "  git commit -m 'R2 security gate: founder sign-off ($DATE_UTC)'"
