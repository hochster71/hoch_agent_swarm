#!/usr/bin/env python3
"""FOUNDER GATE — App Store Connect credentials (authored 2026-07-19 audit).

Drives the ASC credential gate to Michael's last paste, per the founder
interaction doctrine:

  * Prompts for APP_STORE_CONNECT_KEY_ID, APP_STORE_CONNECT_ISSUER_ID, and the
    .p8 private key PATH at HIDDEN native prompts. Nothing is echoed, logged,
    or printed back.
  * VALIDATES the credentials against the real App Store Connect API before
    persisting anything (a paste that cannot authenticate is rejected).
  * On success: persists the three vars into the repo-root .env (gitignored,
    chmod 600), writes the authoritative ASC evidence snapshot
    coordination/evidence/external/asc_epic_fury.json, and re-runs the
    champion-gate + shipped validators + goal engine so TESTFLIGHT /
    APP_STORE_CONNECT / REQ-TO-002 read from LIVE Apple state.

Fail-closed: any error leaves the repo untouched except (possibly) an honest
UNKNOWN evidence snapshot. Never fabricates a PASS.

Run:  python3 scripts/founder/asc_credentials_gate.py
"""
from __future__ import annotations

import datetime
import getpass
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- ceremony identity (2026-07-22 preflight hardening) ---------------------------
# Second-resolution text alone risks collision; identifiers carry microseconds
# plus 64 bits of cryptographic randomness, and contain NO credentials, key
# identifiers, usernames, Apple account identifiers, or machine secrets.
CEREMONY_ID_RE = re.compile(
    r"^ASC-CEREMONY-\d{8}T\d{6}\.\d{6}Z-[0-9a-f]{16}$")


def generate_ceremony_id(now: datetime.datetime | None = None) -> str:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cid = ("ASC-CEREMONY-" + now.strftime("%Y%m%dT%H%M%S.%fZ")
           + "-" + secrets.token_hex(8))
    if not CEREMONY_ID_RE.match(cid):  # fail-closed self-check
        raise RuntimeError("generated ceremony id failed strict format validation")
    return cid


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _git_out(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                           text=True, timeout=60,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _atomic_write_json(path: Path, obj: dict) -> None:
    """temp file in destination dir -> flush -> fsync -> atomic rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent),
                                    prefix=".receipt.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, indent=2) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

# --- re-exec with the repo venv if deps are missing --------------------------------
def _ensure_deps() -> None:
    try:
        import jwt  # noqa: F401
        import requests  # noqa: F401
        return
    except ImportError:
        pass
    venv_py = ROOT / ".venv" / "bin" / "python"
    if os.environ.get("_ASC_GATE_REEXEC") != "1" and venv_py.exists():
        os.environ["_ASC_GATE_REEXEC"] = "1"
        os.execv(str(venv_py), [str(venv_py), __file__] + sys.argv[1:])
    sys.exit("FAIL-CLOSED: no interpreter with 'requests' + 'PyJWT' found "
             "(tried current interpreter and .venv/bin/python). "
             "Install with: .venv/bin/pip install requests PyJWT")


def _prompt_hidden(label: str, current_env: str) -> str:
    existing = (os.environ.get(current_env) or "").strip()
    if existing:
        keep = input(f"{label}: found in environment — reuse it? [Y/n] ").strip().lower()
        if keep in ("", "y", "yes"):
            return existing
    val = getpass.getpass(f"{label} (hidden): ").strip()
    if not val:
        sys.exit(f"FAIL-CLOSED: empty {label}; nothing persisted.")
    return val


def _upsert_env_file(env_path: Path, kv: dict[str, str]) -> None:
    """Atomically upsert keys into env_path, 0600 from the moment of creation.

    2026-07-22 hardening (founder pre-ceremony checklist item 6): the previous
    write_text-then-chmod sequence (a) was not atomic — a crash mid-write could
    corrupt .env — and (b) briefly created a new .env with umask-default
    permissions before the chmod landed. Now the content is written to a
    mkstemp file (unpredictable name, 0600 at creation, same directory) and
    atomically os.replace()d over the target; the temp file is guaranteed
    removed on any failure. Existing unrelated lines are preserved verbatim.
    """
    import tempfile
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in kv:
            out.append(f"{key}={kv[key]}")
            seen.add(key)
        else:
            out.append(line)
    for k, v in kv.items():
        if k not in seen:
            out.append(f"{k}={v}")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(env_path.parent),
                                    prefix=".env.", suffix=".tmp")  # 0600 by mkstemp
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
        os.replace(tmp_name, env_path)  # atomic on POSIX; inherits the 0600 inode
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main() -> int:
    _ensure_deps()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    from goal import asc_client  # the existing fail-closed live reader

    # 2026-07-22 founder verifier requirement: every ceremony run carries a
    # single identifier that downstream artifacts + the recompute receipt share,
    # so post-ceremony verification can correlate one ceremony end-to-end.
    _ceremony_started = datetime.datetime.now(datetime.timezone.utc)
    ceremony_id = generate_ceremony_id(_ceremony_started)
    # provenance captured at ceremony start (before any writes)
    _git_head = _git_out("rev-parse", "HEAD").strip()
    _worktree_digest = _sha256_text(_git_out("status", "--porcelain=v1"))

    print("=" * 70)
    print("FOUNDER GATE — App Store Connect credentials")
    print("Nothing you paste is echoed, logged, or transmitted anywhere except")
    print("to Apple's App Store Connect API for validation.")
    print("=" * 70)

    kid = _prompt_hidden("APP_STORE_CONNECT_KEY_ID (key id)", "APP_STORE_CONNECT_KEY_ID")
    iss = _prompt_hidden("APP_STORE_CONNECT_ISSUER_ID (issuer id)", "APP_STORE_CONNECT_ISSUER_ID")
    p8 = _prompt_hidden("Path to your AuthKey_*.p8 file", "ASC_API_KEY")
    p8_path = Path(os.path.expanduser(p8))
    p8_is_raw_pem = not p8_path.exists() and "BEGIN PRIVATE KEY" in p8
    if not p8_path.exists() and not p8_is_raw_pem:
        sys.exit("FAIL-CLOSED: that .p8 path does not exist; nothing persisted.")
    # 2026-07-22 founder pre-ceremony checklist: warn if the .p8 is readable by
    # group/other. Warn-only — this script never changes permissions itself.
    if p8_path.exists():
        mode = p8_path.stat().st_mode & 0o777
        if mode & 0o077:
            print(f"WARNING: {p8_path} has permissions {oct(mode)} — readable "
                  f"beyond your user. Recommend: chmod 600 '{p8_path}'")

    os.environ["APP_STORE_CONNECT_KEY_ID"] = kid
    os.environ["APP_STORE_CONNECT_ISSUER_ID"] = iss
    os.environ["ASC_API_KEY"] = p8

    # --- validate against the REAL provider before persisting ----------------------
    print("\nValidating against api.appstoreconnect.apple.com ...")
    try:
        bundle_id = os.environ.get("HELM_ASC_BUNDLE_ID") or asc_client.DEFAULT_BUNDLE_ID
        app_id = asc_client._app_id(bundle_id)
    except asc_client.ASCUnavailable as e:
        sys.exit(f"FAIL-CLOSED: App Store Connect rejected the credentials or the "
                 f"read failed ({e}). Nothing persisted.")
    print(f"OK — authenticated; app found for {bundle_id}.")

    # --- persist to gitignored .env (0600) ------------------------------------------
    # 2026-07-22 fix (founder pre-ceremony checklist): NEVER persist raw private-key
    # material. Only the key id, issuer id, and a *path* to the .p8 are written.
    # If PEM contents were pasted, they stay in this process's environment for this
    # run only and are gone when it exits.
    env_kv = {
        "APP_STORE_CONNECT_KEY_ID": kid,
        "APP_STORE_CONNECT_ISSUER_ID": iss,
    }
    if p8_path.exists():
        env_kv["ASC_API_KEY"] = str(p8_path)
    _upsert_env_file(ROOT / ".env", env_kv)
    if p8_is_raw_pem:
        print("Key id + issuer id persisted to .env (gitignored, mode 600). "
              "Raw PEM was NOT persisted anywhere — future gate recomputes will "
              "need the .p8 path; re-run this gate with the file path when ready.")
    else:
        print("Credentials persisted to .env (gitignored, mode 600; .p8 stored "
              "as PATH only — key material never written).")

    # --- write the authoritative ASC evidence snapshot ------------------------------
    observed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        vers = asc_client._get(f"/apps/{app_id}/appStoreVersions", {"limit": 3}).get("data", [])
        attrs = (vers[0]["attributes"] if vers else {}) or {}
        snapshot = {
            "appStoreState": attrs.get("appStoreState") or attrs.get("state"),
            "versionString": attrs.get("versionString"),
            "observed_at": observed_at,
            "bundle_id": bundle_id,
            "ceremony_id": ceremony_id,
            "source": "live App Store Connect read (scripts/founder/asc_credentials_gate.py)",
        }
    except asc_client.ASCUnavailable as e:
        snapshot = {"appStoreState": None, "versionString": None,
                    "observed_at": observed_at, "bundle_id": bundle_id,
                    "ceremony_id": ceremony_id,
                    "source": f"live read FAILED after auth: {e}"}
    ev_dir = ROOT / "coordination" / "evidence" / "external"
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_path = ev_dir / "asc_epic_fury.json"
    ev_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"ASC evidence snapshot written: {ev_path.relative_to(ROOT)} "
          f"(appStoreState={snapshot['appStoreState']})")

    # --- refresh the gates from live state, binding each step's outputs --------------
    def _bind_output(rel: str) -> dict:
        """Digest + timestamp + parsed authoritative state for one output artifact."""
        p = ROOT / rel
        out = {"path": rel, "sha256": None, "timestamp": None,
               "parsed_state": None, "failure_reason": None}
        if not p.exists():
            out["failure_reason"] = "output artifact missing"
            return out
        try:
            out["sha256"] = _sha256_file(p)
            data = json.loads(p.read_text(encoding="utf-8"))
            out["timestamp"] = next(
                (data.get(k) for k in ("generated_at", "computed_at", "read_at",
                                       "updated_at") if data.get(k)), None)
            if rel.endswith("champion_gates.json"):
                out["parsed_state"] = {
                    g.get("gate"): g.get("status") for g in data.get("gates", [])
                    if g.get("gate") in ("TESTFLIGHT", "APP_STORE_CONNECT")}
            elif rel.endswith("shipped_report.json"):
                out["parsed_state"] = {"asc_state": data.get("asc_state"),
                                       "shipped": data.get("shipped")}
            elif rel.endswith("goal_state.json"):
                st = None
                def _walk(o):
                    nonlocal st
                    if isinstance(o, dict):
                        if o.get("id") == "REQ-CP-APP_STORE_CONNECT" and "state" in o \
                                and "validator" in o:
                            st = o["state"]
                        for v in o.values():
                            _walk(v)
                    elif isinstance(o, list):
                        for v in o:
                            _walk(v)
                _walk(data)
                out["parsed_state"] = {"REQ-CP-APP_STORE_CONNECT": st}
            elif rel.endswith("mission_state.json"):
                out["parsed_state"] = {
                    "overall": (data.get("overall") or {}).get("status")}
        except Exception as e:
            out["failure_reason"] = f"unparseable output: {e}"
        return out

    STEPS = [
        {"step": "champion_gate_recompute",
         "script": "scripts/goal/verify_champion_gates.py",
         "outputs": ["coordination/goal/champion_gates.json"],
         "correlation": "receipt-bound digest"},
        {"step": "shipped_recompute",
         "script": "scripts/goal/verify_shipped.py",
         "outputs": ["coordination/goal/shipped_report.json"],
         "correlation": "receipt-bound digest"},
        {"step": "goal_engine_recompute",
         "script": "scripts/goal/goal_engine.py",
         "outputs": ["coordination/goal/goal_state.json",
                     "coordination/goal/mission_state.json"],
         "correlation": "receipt-bound digest"},
    ]
    py = sys.executable
    chain = []
    for spec in STEPS:
        print(f"\n$ {spec['script']}")
        r = subprocess.run([py, spec["script"]], cwd=str(ROOT))
        entry = {
            "step": spec["step"],
            "cmd": spec["script"],
            "returncode": r.returncode,
            "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "correlation": spec["correlation"],
            "outputs": [_bind_output(rel) for rel in spec["outputs"]],
        }
        if r.returncode != 0:
            entry["failure_reason"] = f"step exited {r.returncode}"
        chain.append(entry)
    # Steps intentionally NOT run inside the founder ceremony (runner-owned);
    # recorded explicitly so the verifier correlates them temporally, disclosed.
    chain.append({"step": "pert_regeneration", "cmd": None, "returncode": None,
                  "status": "DEFERRED_TO_POST_GATE_LANE",
                  "outputs": [{"path": "coordination/goal/build_to_goal_status.json"}],
                  "correlation": "temporal(started_at)"})
    chain.append({"step": "doorstep_regeneration", "cmd": None, "returncode": None,
                  "status": "DEFERRED_TO_POST_GATE_LANE",
                  "outputs": [{"path": "coordination/goal/intake_to_doorstep.json"}],
                  "correlation": "temporal(started_at)"})

    # --- ceremony receipt: atomic, uniquely identified, artifact-digest-bound --------
    ceremonies_dir = ev_dir / "asc_ceremonies"
    receipt = {
        "schema": "ASC_CEREMONY_RECEIPT_v2",
        "ceremony_id": ceremony_id,
        "started_at": _ceremony_started.isoformat(),
        "validated_at": observed_at,
        "bundle_id": bundle_id,
        "appStoreState": snapshot.get("appStoreState"),
        "snapshot_binding": {
            "path": str(ev_path.relative_to(ROOT)),
            "sha256": _sha256_file(ev_path),
            "observed_at": snapshot.get("observed_at"),
        },
        "gate_script_digest": _sha256_file(Path(__file__).resolve()),
        "git_head": _git_head,
        "worktree_status_digest_at_start": _worktree_digest,
        "recompute_chain": chain,
        "written_by": "scripts/founder/asc_credentials_gate.py",
        "note": ("Receipt exists only after genuine Apple authentication; written "
                 "atomically (temp+fsync+rename); records recompute exit codes and "
                 "output digests honestly, including failures. Contains no "
                 "credentials, key identifiers, or tokens. Not cryptographically "
                 "signed — digest+ledger bound only."),
    }
    receipt_path = ceremonies_dir / f"{ceremony_id}.json"
    _atomic_write_json(receipt_path, receipt)
    # append-only ceremony ledger: newest entry is the only active authority
    ledger = ceremonies_dir / "LEDGER.jsonl"
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ceremony_id": ceremony_id,
                             "started_at": receipt["started_at"],
                             "receipt_sha256": _sha256_file(receipt_path)}) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    print(f"Ceremony receipt written atomically: "
          f"{receipt_path.relative_to(ROOT)} ({ceremony_id})")

    failed_steps = [c["cmd"] for c in chain
                    if c.get("returncode") not in (0, None)]
    if failed_steps:
        print(f"\nWARNING: recompute step(s) exited nonzero: {failed_steps}. "
              "Runtime truth may be partially refreshed; the post-ceremony "
              "verifier will fail closed on this receipt.")
        return 1
    print("\nDone. TESTFLIGHT / APP_STORE_CONNECT / REQ-TO-002 now reflect live Apple state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
