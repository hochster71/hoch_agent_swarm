#!/usr/bin/env python3
"""Post-ceremony verification v3 — founder-required evidence order + replay
protection (2026-07-22 preflight closeout).

Read-only. Evaluates the authoritative runtime artifacts AFTER the founder
completes scripts/founder/asc_credentials_gate.py. Fail-closed: missing,
malformed, stale, uncorrelated, duplicated, rolled-back, or inconsistent
evidence produces explicit failures and a nonzero exit — never an inferred
status.

Receipt model (ASC_CEREMONY_RECEIPT_v2): each ceremony writes an atomic
(temp+fsync+rename) receipt at
coordination/evidence/external/asc_ceremonies/<ceremony_id>.json and appends
to an append-only LEDGER.jsonl. Authority rules enforced here:

  R1  the receipt store must be clean: no temp/partial files, no malformed
      receipts, no duplicate internal ceremony ids, no filename/internal-id
      disagreement, no invalid id format
  R2  exactly ONE receipt is active: the newest by started_at, and it must be
      the last ledger entry; every older receipt is superseded (consumed);
      if the newest receipt is invalid there is NO fallback to an older one
  R3  the active receipt must be within the freshness window
  R4  the Apple snapshot digest is recomputed and must equal the receipt's
      recorded digest, and share its ceremony_id (identity correlation)
  R5  the gate script digest must match the receipt (the ceremony must have
      run the code currently on disk)
  R6  every receipt-bound recompute output must: have exited 0, exist now,
      parse, and not PREDATE its receipt-recorded timestamp (rollback
      rejection). An identical digest is 'digest-verified'; a newer artifact
      is 'superseded by a later recompute' (allowed, runner-owned files); a
      changed digest WITHOUT a newer timestamp is tampering -> FAIL
  R7  no chain-level PASS while any subordinate output is absent, stale,
      malformed, digest-inconsistent, or policy-inconsistent

Apple policy (exact, unchanged): acceptance set READY_FOR_SALE /
READY_FOR_DISTRIBUTION / PENDING_DEVELOPER_RELEASE / PROCESSING_FOR_APP_STORE.
IN_REVIEW-class states -> EXTERNAL-PENDING (advisory). Rejection states ->
FAIL. Unknown or unmapped states -> FAIL CLOSED. The observed state is always
printed verbatim; nothing non-accepted is ever mapped to satisfied.

Self no-mutation proof: `git status --porcelain` (GIT_OPTIONAL_LOCKS=0) is
captured before and after all reads and any difference is a verifier failure.

Limits disclosed: receipts are digest+ledger bound, NOT cryptographically
signed — there is no signer nonrepudiation.

Run:  .venv/bin/python scripts/goal/verify_post_asc_ceremony.py
Exit: 0 only when every ceremony-controllable item is confirmed. N3 and the
      Security High finding remain advisory and the overall posture line
      always reads WITHHELD until they clear.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_AGE_HOURS = 6.0

CEREMONIES_DIR = "coordination/evidence/external/asc_ceremonies"
LEDGER = CEREMONIES_DIR + "/LEDGER.jsonl"
SNAPSHOT = "coordination/evidence/external/asc_epic_fury.json"
GATE_SCRIPT = "scripts/founder/asc_credentials_gate.py"
GATES = "coordination/goal/champion_gates.json"
GOAL_STATE = "coordination/goal/goal_state.json"
MISSION = "coordination/goal/mission_state.json"
SHIPPED = "coordination/goal/shipped_report.json"
B2G = "coordination/goal/build_to_goal_status.json"
DOORSTEP = "coordination/goal/intake_to_doorstep.json"
SECURITY = "coordination/security/helm_control_posture.json"

CEREMONY_ID_RE = re.compile(r"^ASC-CEREMONY-\d{8}T\d{6}\.\d{6}Z-[0-9a-f]{16}$")

# Exact policy sets — acceptance mirrors scripts/goal/asc_client.py LIVE set.
ASC_ACCEPT = {"READY_FOR_SALE", "READY_FOR_DISTRIBUTION",
              "PENDING_DEVELOPER_RELEASE", "PROCESSING_FOR_APP_STORE"}
ASC_REJECT = {"REJECTED", "DEVELOPER_REJECTED", "METADATA_REJECTED",
              "INVALID_BINARY"}
ASC_IN_PROGRESS = {"IN_REVIEW", "WAITING_FOR_REVIEW", "READY_FOR_REVIEW",
                   "PREPARE_FOR_SUBMISSION"}


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_ts(iso):
    try:
        return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except Exception:
        return None


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _art(root: Path, rel: str):
    p = root / rel
    info = {"path": rel, "exists": p.exists(), "sha256": None, "data": None,
            "malformed": False}
    if p.exists():
        try:
            raw = p.read_bytes()
            info["sha256"] = _sha256_bytes(raw)
            info["data"] = json.loads(raw.decode("utf-8"))
        except Exception:
            info["malformed"] = True
    return info


def _git_status(root: Path):
    try:
        r = subprocess.run(["git", "status", "--porcelain=v1"],
                           cwd=str(root), capture_output=True, text=True,
                           timeout=60,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def _select_receipt(root: Path):
    """Enforce R1/R2. Returns (receipt_dict|None, integrity_failures, detail)."""
    fails = []
    cdir = root / CEREMONIES_DIR
    if not cdir.is_dir():
        return None, ["ceremony store missing (no ceremony has run)"], None
    entries = sorted(cdir.iterdir())
    temp = [e.name for e in entries
            if e.name.endswith(".tmp") or e.name.startswith(".receipt.")]
    if temp:
        fails.append(f"temporary/partial receipt file(s) present: {temp}")
    receipts = []
    seen_ids = {}
    for e in entries:
        if e.suffix != ".json" or e.name == "LEDGER.jsonl":
            continue
        try:
            data = json.loads(e.read_bytes().decode("utf-8"))
        except Exception:
            fails.append(f"partially written / malformed receipt: {e.name}")
            continue
        cid = data.get("ceremony_id")
        if not cid or not CEREMONY_ID_RE.match(str(cid)):
            fails.append(f"invalid ceremony_id format in {e.name}: {cid!r}")
            continue
        if e.stem != cid:
            fails.append(f"filename/internal-id disagreement: file {e.name} "
                         f"contains ceremony_id {cid}")
            continue
        if cid in seen_ids:
            fails.append(f"duplicate receipts for ceremony_id {cid}")
            continue
        seen_ids[cid] = True
        receipts.append((data, e))
    if not receipts:
        fails.append("no valid receipt in ceremony store")
        return None, fails, None
    dated = [(r, _parse_ts(r[0].get("started_at"))) for r in receipts]
    if any(ts is None for _, ts in dated):
        fails.append("receipt with unparseable started_at present — no "
                     "authority can be established (no fallback)")
        return None, fails, None
    dated.sort(key=lambda x: x[1])
    if len(dated) >= 2 and dated[-1][1] == dated[-2][1]:
        fails.append("two receipts claim the same started_at — ambiguous "
                     "authority, refusing both")
        return None, fails, None
    active, _ = dated[-1]
    # ledger: the active receipt must be the LAST accepted entry (rollback and
    # consumed-receipt protection). An older receipt can never regain authority.
    led = root / LEDGER
    if not led.exists():
        fails.append("ceremony LEDGER.jsonl missing")
    else:
        try:
            lines = [json.loads(x) for x in
                     led.read_text(encoding="utf-8").splitlines() if x.strip()]
            if not lines:
                fails.append("ceremony ledger is empty")
            elif lines[-1].get("ceremony_id") != active[0].get("ceremony_id"):
                fails.append(
                    f"active receipt {active[0].get('ceremony_id')} is not the "
                    f"last ledger entry ({lines[-1].get('ceremony_id')}) — "
                    "superseded/rolled-back receipt rejected")
        except Exception:
            fails.append("ceremony ledger malformed")
    if fails:
        return None, fails, active[0].get("ceremony_id")
    return active[0], [], active[0].get("ceremony_id")


def run(root: Path):
    rows = []

    def row(label, status, ok, source=None, sha=None, ts=None, value=None,
            reason="", correlation=None):
        rows.append({"label": label, "status": status, "ok": ok,
                     "source": source, "sha256": sha, "ts": ts, "value": value,
                     "reason": reason, "correlation": correlation})

    git_before = _git_status(root)

    snap = _art(root, SNAPSHOT)
    gates = _art(root, GATES)
    goal = _art(root, GOAL_STATE)
    mission = _art(root, MISSION)
    shipped = _art(root, SHIPPED)
    b2g = _art(root, B2G)
    door = _art(root, DOORSTEP)
    sec = _art(root, SECURITY)

    def bad(a):
        if not a["exists"]:
            return "artifact missing"
        if a["malformed"]:
            return "artifact malformed (unparseable JSON)"
        return None

    # --- R1/R2: receipt store integrity + single active authority --------------------
    rcpt, store_fails, active_cid = _select_receipt(root)
    if store_fails:
        row("Ceremony receipt store", "FAIL", False, CEREMONIES_DIR, None, None,
            active_cid, "; ".join(store_fails))
    else:
        row("Ceremony receipt store", "PASS", True, CEREMONIES_DIR, None, None,
            active_cid, "clean store; single active receipt = last ledger entry",
            correlation="ledger")

    started_at = None
    rcpt_ok = False
    if rcpt is not None:
        started_at = _parse_ts(rcpt.get("started_at"))
        age_h = ((_utcnow() - started_at).total_seconds() / 3600.0
                 if started_at else None)
        snap_cid = (snap["data"] or {}).get("ceremony_id") if not bad(snap) else None
        if rcpt.get("schema") != "ASC_CEREMONY_RECEIPT_v2":
            row("Ceremony receipt & identity", "FAIL", False, CEREMONIES_DIR,
                None, rcpt.get("started_at"), active_cid,
                f"unexpected schema {rcpt.get('schema')!r}")
        elif age_h is None or age_h > MAX_AGE_HOURS:
            row("Ceremony receipt & identity", "FAIL", False, CEREMONIES_DIR,
                None, rcpt.get("started_at"), active_cid,
                f"receipt age {None if age_h is None else round(age_h, 1)}h "
                f"exceeds freshness window {MAX_AGE_HOURS}h")
        elif rcpt.get("ceremony_id") != snap_cid:
            row("Ceremony receipt & identity", "FAIL", False, CEREMONIES_DIR,
                None, rcpt.get("started_at"), active_cid,
                f"identity mismatch: snapshot ceremony_id={snap_cid!r}",
                correlation="identity")
        else:
            rcpt_ok = True
            row("Ceremony receipt & identity", "PASS", True, CEREMONIES_DIR,
                None, rcpt.get("started_at"), active_cid,
                f"fresh ({age_h:.1f}h); receipt and Apple evidence share one "
                "ceremony_id", correlation="identity")
    elif not store_fails:
        row("Ceremony receipt & identity", "FAIL", False, CEREMONIES_DIR, None,
            None, None, "no active receipt")

    def after_ceremony(iso):
        ts = _parse_ts(iso)
        if not (started_at and ts):
            return False, None
        return ts >= started_at, (_utcnow() - ts).total_seconds() / 3600.0

    # --- R4: Apple snapshot digest binding -------------------------------------------
    raw_state = None if bad(snap) else (snap["data"] or {}).get("appStoreState")
    if rcpt_ok:
        sb = rcpt.get("snapshot_binding") or {}
        if bad(snap):
            row("Apple snapshot digest binding", "FAIL", False, SNAPSHOT,
                snap["sha256"], None, None, bad(snap))
        elif not sb.get("sha256"):
            row("Apple snapshot digest binding", "FAIL", False, SNAPSHOT,
                snap["sha256"], sb.get("observed_at"), raw_state,
                "receipt lacks snapshot digest binding")
        elif sb["sha256"] != snap["sha256"]:
            row("Apple snapshot digest binding", "FAIL", False, SNAPSHOT,
                snap["sha256"], sb.get("observed_at"), raw_state,
                f"recomputed digest {snap['sha256'][:12]} != receipt-recorded "
                f"{str(sb['sha256'])[:12]} — snapshot changed after ceremony")
        else:
            row("Apple snapshot digest binding", "PASS", True, SNAPSHOT,
                snap["sha256"], sb.get("observed_at"), raw_state,
                "independently recomputed digest matches receipt",
                correlation="identity+digest")
    else:
        row("Apple snapshot digest binding", "FAIL", False, SNAPSHOT,
            snap["sha256"], None, raw_state, "no valid active receipt")

    # --- 1-2. Apple authentication + evidence snapshot -------------------------------
    problem = bad(snap)
    if problem:
        row("Apple API authentication", "FAIL", False, SNAPSHOT, snap["sha256"],
            None, None, problem)
        row("Credential evidence snapshot", "FAIL", False, SNAPSHOT,
            snap["sha256"], None, None, problem)
    else:
        d = snap["data"]
        obs = d.get("observed_at")
        ts = _parse_ts(obs)
        age = (_utcnow() - ts).total_seconds() / 3600.0 if ts else None
        fresh = age is not None and age <= MAX_AGE_HOURS
        auth_ok = bool(fresh and raw_state and d.get("ceremony_id") and rcpt_ok)
        row("Apple API authentication", "PASS" if auth_ok else "NOT-CONFIRMED",
            auth_ok, SNAPSHOT, snap["sha256"], obs, raw_state,
            (f"fresh ({age:.1f}h), ceremony-correlated" if auth_ok else
             f"age={None if age is None else round(age, 1)}h "
             f"state={raw_state!r} ceremony_id={d.get('ceremony_id')!r} "
             f"receipt_ok={rcpt_ok} (max {MAX_AGE_HOURS}h)"),
            correlation="identity")
        row("Credential evidence snapshot",
            "CREATED" if auth_ok else "NOT-CONFIRMED", auth_ok, SNAPSHOT,
            snap["sha256"], obs, d.get("versionString"),
            "written by gate after genuine Apple authentication" if auth_ok
            else "see Apple API authentication")

    # --- R5: gate script digest binding ----------------------------------------------
    gate_file = root / GATE_SCRIPT
    if rcpt_ok:
        rec_dig = rcpt.get("gate_script_digest")
        cur_dig = (_sha256_bytes(gate_file.read_bytes())
                   if gate_file.exists() else None)
        ok = bool(rec_dig and cur_dig and rec_dig == cur_dig)
        row("Gate script digest binding", "PASS" if ok else "FAIL", ok,
            GATE_SCRIPT, cur_dig, None, rcpt.get("git_head"),
            "ceremony ran the gate code currently on disk" if ok else
            "gate script digest mismatch or unrecorded — ceremony code and "
            "on-disk code differ")
    else:
        row("Gate script digest binding", "FAIL", False, GATE_SCRIPT, None,
            None, None, "no valid active receipt")

    # --- 3. REQ-CP-APP_STORE_CONNECT under exact policy states -----------------------
    req_states = {}
    if not bad(goal):
        def _walk(o):
            if isinstance(o, dict):
                if (o.get("id", "").startswith("REQ") and "state" in o
                        and "validator" in o):
                    req_states[o["id"]] = o
                for v in o.values():
                    _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)
        _walk(goal["data"])
    req = req_states.get("REQ-CP-APP_STORE_CONNECT")
    if bad(goal) or req is None:
        row("REQ-CP-APP_STORE_CONNECT", "FAIL", False, GOAL_STATE,
            goal["sha256"], None, None,
            bad(goal) or "requirement absent from goal_state")
    else:
        st = req.get("state")
        if raw_state in ASC_ACCEPT and st == "SATISFIED":
            row("REQ-CP-APP_STORE_CONNECT", "SATISFIED", True, GOAL_STATE,
                goal["sha256"], req.get("checked_at"), raw_state,
                f"Apple state {raw_state} is in the exact acceptance set")
        elif st == "SATISFIED":
            row("REQ-CP-APP_STORE_CONNECT", "INCONSISTENT", False, GOAL_STATE,
                goal["sha256"], req.get("checked_at"), raw_state,
                f"goal_state says SATISFIED but Apple state {raw_state!r} is "
                "not in the policy acceptance set — refusing to promote")
        elif raw_state in ASC_REJECT:
            row("REQ-CP-APP_STORE_CONNECT", f"FAILED:{raw_state}", False,
                GOAL_STATE, goal["sha256"], req.get("checked_at"), raw_state,
                "Apple rejected — external gate genuinely failed")
        elif raw_state in ASC_IN_PROGRESS:
            row("REQ-CP-APP_STORE_CONNECT", f"EXTERNAL-PENDING:{st}", None,
                GOAL_STATE, goal["sha256"], req.get("checked_at"), raw_state,
                f"Apple state {raw_state} is a known in-progress state; "
                "requirement honestly unsatisfied pending Apple (advisory)")
        else:
            row("REQ-CP-APP_STORE_CONNECT", f"FAIL-CLOSED:{raw_state}", False,
                GOAL_STATE, goal["sha256"], req.get("checked_at"), raw_state,
                f"Apple state {raw_state!r} is not in any mapped policy set "
                "(accept / reject / in-progress) — failing closed")

    # --- 4-5. Runtime truth updated from live read -----------------------------------
    problem = bad(gates)
    gsat = None if problem else (gates["data"] or {}).get("generated_at")
    g_post, g_age = after_ceremony(gsat)
    by_gate = {} if problem else {g.get("gate"): g for g in
                                  gates["data"].get("gates", [])}
    for gate, label in (("TESTFLIGHT", "TESTFLIGHT runtime truth"),
                        ("APP_STORE_CONNECT", "APP_STORE_CONNECT runtime truth")):
        g = by_gate.get(gate, {})
        st = g.get("status", "ABSENT")
        live_read = any(str(e).startswith("asc:") and str(e) != "asc:none"
                        for e in (g.get("evidence") or []))
        ok = bool(rcpt_ok and g_post and (g_age or 0) <= MAX_AGE_HOURS
                  and live_read and not problem)
        row(label, f"UPDATED:{st}" if ok else f"NOT-UPDATED:{st}", ok, GATES,
            gates["sha256"], gsat, st,
            (problem or ("live ASC read recomputed after ceremony start "
                         "(status reported verbatim)" if ok else
                         "no live post-ceremony ASC read")),
            correlation="temporal(started_at)")

    # --- 6. REQ-TO-002 ---------------------------------------------------------------
    problem = bad(shipped)
    s = {} if problem else shipped["data"]
    s_post, s_age = after_ceremony(s.get("read_at"))
    creds_missing = "not set" in str(s.get("asc_detail") or "")
    ok = bool(rcpt_ok and s_post and (s_age or 0) <= MAX_AGE_HOURS
              and not creds_missing and not problem)
    row("REQ-TO-002", "RECOMPUTED" if ok else "NOT-RECOMPUTED", ok, SHIPPED,
        shipped["sha256"], s.get("read_at"),
        f"asc_state={s.get('asc_state')} shipped={s.get('shipped')}",
        problem or ("credentialed live re-read after ceremony start" if ok
                    else "no credentialed post-ceremony live read"),
        correlation="temporal(started_at)")

    # --- R6/R7: receipt-bound recompute steps, outputs verified individually ---------
    chain = (rcpt or {}).get("recompute_chain", []) if rcpt_ok else []
    current = {GATES: gates, SHIPPED: shipped, GOAL_STATE: goal,
               MISSION: mission}

    def verify_step(step_name, label):
        entry = next((c for c in chain if c.get("step") == step_name), None)
        if entry is None:
            row(label, "FAIL", False, CEREMONIES_DIR, None, None, None,
                f"receipt has no '{step_name}' entry")
            return
        if entry.get("returncode") != 0:
            row(label, "FAIL", False, CEREMONIES_DIR, None,
                entry.get("completed_at"), None,
                entry.get("failure_reason") or
                f"step exited {entry.get('returncode')}")
            return
        problems, verified = [], []
        for out in entry.get("outputs", []):
            rel = out.get("path")
            cur = current.get(rel) or _art(root, rel)
            p = bad(cur)
            if p:
                problems.append(f"{rel}: {p}")
                continue
            rec_sha, rec_ts = out.get("sha256"), _parse_ts(out.get("timestamp"))
            cur_ts = _parse_ts(next(
                (cur["data"].get(k) for k in
                 ("generated_at", "computed_at", "read_at", "updated_at")
                 if cur["data"].get(k)), None))
            if not rec_sha or rec_ts is None:
                problems.append(f"{rel}: receipt lacks digest/timestamp binding")
            elif cur_ts is None:
                problems.append(f"{rel}: current artifact has no timestamp")
            elif cur_ts < rec_ts:
                problems.append(f"{rel}: current artifact PREDATES receipt-bound "
                                "output — rollback rejected")
            elif cur["sha256"] == rec_sha:
                verified.append(f"{rel}: digest-verified")
            elif cur_ts > rec_ts:
                verified.append(f"{rel}: superseded by later recompute (allowed; "
                                "runner-owned artifact)")
            else:
                problems.append(f"{rel}: digest changed without a newer "
                                "timestamp — tampering suspected")
        if problems:
            row(label, "FAIL", False, CEREMONIES_DIR, None,
                entry.get("completed_at"), None, "; ".join(problems),
                correlation="receipt-bound digest")
        else:
            row(label, "PASS", True, CEREMONIES_DIR, None,
                entry.get("completed_at"), entry.get("cmd"),
                "; ".join(verified), correlation="receipt-bound digest")

    verify_step("champion_gate_recompute", "Champion-gate recomputation")
    verify_step("goal_engine_recompute", "Goal-engine recomputation")

    # --- 9-10. PERT + Doorstep (deferred steps; temporal correlation, disclosed) -----
    problem = bad(b2g)
    b = {} if problem else b2g["data"]
    b_post, b_age = after_ceremony(b.get("updated_at"))
    ok = bool(rcpt_ok and b_post and (b_age or 0) <= MAX_AGE_HOURS and not problem)
    row("PERT regeneration", "PASS" if ok else "NOT-REGENERATED", ok, B2G,
        b2g["sha256"], b.get("updated_at"),
        f"{b.get('percent_to_goal')}% state={b.get('state')}",
        problem or ("updated after ceremony start (runner-owned; receipt "
                    "records this step as deferred)" if ok else
                    "not updated after ceremony start"),
        correlation="temporal(started_at)")
    problem = bad(door)
    dd = {} if problem else door["data"]
    d_ts = dd.get("computed_at") or dd.get("generated_at") or dd.get("updated_at")
    d_post, d_age = after_ceremony(d_ts)
    ok = bool(rcpt_ok and d_post and (d_age or 0) <= MAX_AGE_HOURS and not problem)
    row("Doorstep packet regeneration", "PASS" if ok else "NOT-REGENERATED",
        ok, DOORSTEP, door["sha256"], d_ts, None,
        problem or ("regenerated after ceremony" if ok else
                    "must be regenerated after the ceremony (post-gate lane)"),
        correlation="temporal(started_at)")

    # --- advisory gates --------------------------------------------------------------
    n3 = (b.get("nodes") or {}).get("N3_VERIFY", "ABSENT")
    row("N3 bound independent verification", str(n3), None, B2G, b2g["sha256"],
        b.get("updated_at"), n3,
        "requires candidate HEAD+tree SHA, SCOPE: COMPOSED_RUNTIME, "
        "re-execution — auditor gate")
    sd = {} if bad(sec) else sec["data"]
    row("Security High finding disposition", "PENDING", None, SECURITY,
        sec["sha256"], sd.get("assessed_at"),
        f"{sd.get('posture_percent')}% of {sd.get('controls_assessed')} sampled",
        "sampled-controls posture only; not full-catalog / not ATO — "
        "founder/auditor gate")

    # --- no-mutation proof -----------------------------------------------------------
    git_after = _git_status(root)
    if git_before is None or git_after is None:
        row("Verifier no-mutation proof", "NOT-APPLICABLE", None, ".git", None,
            None, None, "git status unavailable in this root")
    elif git_before == git_after:
        row("Verifier no-mutation proof", "PASS", True, ".git",
            _sha256_bytes(git_before.encode())[:12], None,
            f"{len(git_before.splitlines())} entries unchanged",
            "git status --porcelain identical before and after all reads")
    else:
        row("Verifier no-mutation proof", "FAIL", False, ".git", None, None,
            None, "working tree changed during verification run")

    controllable_ok = all(r["ok"] for r in rows if r["ok"] is not None)
    row("Overall posture", "WITHHELD", None, None, None, None, None,
        "external gates open (N3, Security)" if controllable_ok
        else "ceremony-controllable items not confirmed")
    return rows, (0 if controllable_ok else 1)


def main() -> int:
    root = ROOT
    if len(sys.argv) == 3 and sys.argv[1] == "--root":
        root = Path(sys.argv[2])  # test harness use only
    rows, code = run(root)
    print("=" * 76)
    print("POST-CEREMONY VERIFICATION v3 — authoritative artifacts, read-only")
    print("=" * 76)
    for r in rows:
        mark = " " if r["ok"] is None else ("✓" if r["ok"] else "✗")
        print(f"{mark} {r['label']:<36} {r['status']}")
        if r["source"]:
            sha = (r["sha256"] or "")[:12] or "-"
            print(f"    source: {r['source']}  sha256:{sha}  ts:{r['ts'] or '-'}")
        if r["value"] is not None:
            print(f"    value:  {r['value']}")
        if r["reason"]:
            print(f"    reason: {r['reason']}"
                  + (f"  [correlation: {r['correlation']}]"
                     if r["correlation"] else ""))
    print("=" * 76)
    print("Limits disclosed: receipts are digest+ledger bound, not "
          "cryptographically signed (no signer nonrepudiation); PERT and "
          "doorstep artifacts carry no native ceremony field, so their "
          "correlation is temporal against the active receipt.")
    print("Doctrine: a successful Apple response is not overall GO; posture "
          "stays WITHHELD until N3 + Security clear.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
