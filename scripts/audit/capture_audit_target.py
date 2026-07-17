#!/usr/bin/env python3
"""capture_audit_target.py — freeze a DIRTY worktree into an immutable, hashed audit target.

Implements the HELM Mission Assurance Audit v2.1 requirement: a commit hash over a dirty
tree is disclosure, not a frozen target. This produces a cryptographic target identity
(audit_target_id) so ChatGPT and Grok can prove they audited the SAME state, and Claude can
distinguish auditor-disagreement from runtime-drift.

NEVER hashes or reads secret file CONTENT — secret-bearing files get metadata only.
Dependency trees (node_modules/.venv) are inventoried at package/lockfile level, not per-file.
Authoritative mutable ledgers are copied into a read-only timestamped snapshot before hashing.

Output: docs/evidence/audit/target/{audit_target.json, git_status_porcelain_v2.txt,
tracked_worktree.patch, staged.patch, untracked_files.json, audit_relevant_hashes.json,
environment.json, runtime_state_snapshot/, SHA256SUMS}

Usage: python3 scripts/audit/capture_audit_target.py
"""
import hashlib, json, os, re, shutil, subprocess, sys, platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
OUT = ROOT / "docs" / "evidence" / "audit" / "target"
SNAP = OUT / "runtime_state_snapshot"

SECRET_RE = re.compile(r"(^|/)(\.env(\.local|\.production.*)?$|\.asc\.env$|.*\.p8$|.*\.pem$|.*\.key$|id_rsa|.*secret.*|.*token.*|private_keys/)", re.I)
DEP_RE = re.compile(r"(^|/)(node_modules|\.venv|site-packages)(/|$)")
CACHE_RE = re.compile(r"(__pycache__|\.pytest_cache|\.mypy_cache|\.DS_Store|\.pyc$|/\.cache/|\.next/cache/)")
BUILD_RE = re.compile(r"(^|/)(build|dist)/|\.ipa$|\.xcarchive|\.next/(?!cache)")
GEN_EVIDENCE_RE = re.compile(r"docs/evidence/audit/|live_proof_packages/|data/backups/.*\.log$|\.bak(\.[0-9]+)?$|\.lock(\.[0-9]+.*)?$")
RUNTIME_RE = re.compile(r"(coordination/.*\.jsonl$|coordination/(goal|council|products|founder)/.*\.json$|\.db$|ledger|active_runtime_source\.json$|factory_registry\.json$|mission_state\.json$)", re.I)
SOURCE_RE = re.compile(r"\.(py|js|ts|tsx|jsx|html|css|sh|yml|yaml|toml|cfg|ini|mjs|cjs)$|(^|/)(Dockerfile|Makefile)|requirements.*\.txt$|package\.json$|uv\.lock$|package-lock\.json$|capacitor\.config\.")

def _now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def _git(*a): return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout
def _sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def _sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def classify(path: str) -> str:
    if SECRET_RE.search(path): return "SECRET_OR_SENSITIVE"
    if DEP_RE.search(path): return "DEPENDENCY_TREE"
    if GEN_EVIDENCE_RE.search(path): return "GENERATED_EVIDENCE"
    if CACHE_RE.search(path): return "CACHE"
    if BUILD_RE.search(path): return "BUILD_OUTPUT"
    if RUNTIME_RE.search(path): return "RUNTIME_STATE"
    if SOURCE_RE.search(path): return "SOURCE_CHANGE"
    return "IRRELEVANT_TO_AUDIT"

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True); SNAP.mkdir(parents=True, exist_ok=True)
    commit = _git("rev-parse", "HEAD").strip()
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()

    (OUT / "git_status_porcelain_v2.txt").write_text(_git("status", "--porcelain=v2", "--branch"))
    tracked_patch = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=ROOT, capture_output=True).stdout
    staged_patch = subprocess.run(["git", "diff", "--binary", "--cached", "HEAD"], cwd=ROOT, capture_output=True).stdout
    (OUT / "tracked_worktree.patch").write_bytes(tracked_patch)
    (OUT / "staged.patch").write_bytes(staged_patch)
    tracked_hash = _sha256_bytes(tracked_patch)
    staged_hash = _sha256_bytes(staged_patch)

    # untracked + modified tracked paths, classified
    untracked = [l for l in _git("ls-files", "--others", "--exclude-standard").splitlines() if l.strip()]
    modified = [l[3:] for l in _git("status", "--porcelain").splitlines() if l and l[:2].strip()]
    all_paths = sorted(set(untracked) | set(modified))

    entries, audit_relevant_hashes, snap_hashes, dep_inventory = [], {}, [], {}
    for rel in all_paths:
        p = ROOT / rel
        cls = classify(rel)
        e = {"path": rel, "classification": cls, "tracked": rel in modified}
        try:
            st = p.stat()
            e.update({"size": st.st_size, "mode": oct(st.st_mode & 0o777), "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        except Exception:
            e["exists"] = False; entries.append(e); continue
        if cls == "SECRET_OR_SENSITIVE":
            e["note"] = "metadata only — content never hashed/read"
        elif cls == "DEPENDENCY_TREE":
            pass  # inventoried separately
        elif cls in ("SOURCE_CHANGE", "RUNTIME_STATE") and p.is_file():
            try:
                if cls == "RUNTIME_STATE":
                    dest = SNAP / rel.replace("/", "__")
                    shutil.copy2(p, dest)  # read-only snapshot of mutable state
                    h = _sha256_file(dest); snap_hashes.append(h)
                    e["snapshot"] = str(dest.relative_to(OUT)); e["source_process"] = "daemon/live"
                else:
                    h = _sha256_file(p)
                e["sha256"] = h; audit_relevant_hashes[rel] = h
            except Exception as ex:
                e["hash_error"] = str(ex)
        entries.append(e)

    # dependency inventory (lockfile hash + count, never per-file)
    for lock in ["uv.lock", "package-lock.json"]:
        lp = ROOT / lock
        if lp.exists():
            dep_inventory[lock] = {"sha256": _sha256_file(lp), "size": lp.stat().st_size}
    nm = list(ROOT.glob("products/*/node_modules"))
    dep_inventory["node_modules_dirs"] = [{"path": str(d.relative_to(ROOT)), "file_count": sum(1 for _ in d.rglob("*"))} for d in nm]
    dep_inventory_hash = _sha256_bytes(json.dumps(dep_inventory, sort_keys=True).encode())

    environment = {
        "host_os": platform.platform(), "arch": platform.machine(),
        "python": platform.python_version(),
        "node": subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip() or "absent",
        "docker": subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip() or "absent",
        "captured_at_utc": _now(),
    }
    env_hash = _sha256_bytes(json.dumps(environment, sort_keys=True).encode())
    (OUT / "environment.json").write_text(json.dumps(environment, indent=2))

    untracked_manifest = {"count": len(entries), "by_class": {}, "entries": entries}
    for e in entries: untracked_manifest["by_class"][e["classification"]] = untracked_manifest["by_class"].get(e["classification"], 0) + 1
    (OUT / "untracked_files.json").write_text(json.dumps(untracked_manifest, indent=2))
    (OUT / "audit_relevant_hashes.json").write_text(json.dumps(audit_relevant_hashes, indent=2))
    untracked_manifest_hash = _sha256_bytes(json.dumps(untracked_manifest, sort_keys=True).encode())
    runtime_snapshot_hash = _sha256_bytes("".join(sorted(snap_hashes)).encode())

    audit_target_id = _sha256_bytes(
        (commit + tracked_hash + staged_hash + untracked_manifest_hash + runtime_snapshot_hash + dep_inventory_hash + env_hash).encode()
    )

    target = {
        "audit_target_id": audit_target_id,
        "repository": "~/hoch_agent_swarm", "branch": branch, "git_commit": commit,
        "working_tree_state": "DIRTY" if all_paths else "CLEAN",
        "captured_at_utc": _now(),
        "components": {
            "git_commit": commit, "tracked_diff_sha256": tracked_hash, "staged_diff_sha256": staged_hash,
            "untracked_manifest_sha256": untracked_manifest_hash, "runtime_state_snapshot_sha256": runtime_snapshot_hash,
            "dependency_inventory_sha256": dep_inventory_hash, "environment_manifest_sha256": env_hash,
        },
        "dependency_inventory": dep_inventory,
        "path_class_counts": untracked_manifest["by_class"],
        "secret_paths_metadata_only": [e["path"] for e in entries if e["classification"] == "SECRET_OR_SENSITIVE"],
        "rule": "Both auditors MUST verify this exact audit_target_id before testing. Divergence => verdict BLOCKED, reason AUDIT_TARGET_DIVERGENCE.",
    }
    (OUT / "audit_target.json").write_text(json.dumps(target, indent=2))

    # SHA256SUMS over the manifest set
    sums = []
    for f in ["audit_target.json", "git_status_porcelain_v2.txt", "tracked_worktree.patch", "staged.patch",
              "untracked_files.json", "audit_relevant_hashes.json", "environment.json"]:
        fp = OUT / f
        if fp.exists(): sums.append(f"{_sha256_file(fp)}  {f}")
    (OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")

    print("AUDIT TARGET FROZEN")
    print("  audit_target_id:", audit_target_id)
    print("  git_commit:", commit, "| branch:", branch)
    print("  dirty paths:", len(all_paths), "| classes:", untracked_manifest["by_class"])
    print("  secret paths (metadata only):", len(target["secret_paths_metadata_only"]))
    print("  output:", OUT)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
