#!/usr/bin/env python3
"""
make_safe_handoff.py — fail-closed Kimi handoff packager.

Takes monorepo (or other) paths, denies crown-jewel trees, redacts secrets,
optionally renames sensitive tokens, and drops a pack into:

  ~/Documents/kimi/workspace/_inbox_from_helm/<pack_id>/

Exit codes:
  0  pack written
  1  denied path / secret residual / validation failure
  2  usage / IO error
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_DENY = SCRIPT_DIR / "deny_paths.txt"
DEFAULT_TOKEN_MAP = SCRIPT_DIR / "token_map.txt"
DEFAULT_TEMPLATE = SCRIPT_DIR / "templates" / "KIMI_SAFE_TASK.md"
DEFAULT_INBOX = Path.home() / "Documents" / "kimi" / "workspace" / "_inbox_from_helm"

# Binary / skip extensions
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".tgz",
    ".gz", ".bz2", ".xz", ".7z", ".dylib", ".so", ".o", ".a", ".wasm",
    ".mp4", ".mov", ".mp3", ".wav", ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot", ".bin", ".pyc", ".pyo",
}

# Secret patterns: (name, regex, replacement)
SECRET_SPECS: list[tuple[str, re.Pattern[str], str]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "REDACTED_AWS_ACCESS_KEY"),
    ("aws_secret", re.compile(r"(?i)(aws_secret_access_key|secret_access_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{30,}"), r"\1=REDACTED_AWS_SECRET"),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "REDACTED_GITHUB_PAT"),
    ("github_fine", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "REDACTED_GITHUB_FINE_PAT"),
    ("gitlab_pat", re.compile(r"\bglpat-[A-Za-z0-9\-_]{20,}\b"), "REDACTED_GITLAB_PAT"),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "REDACTED_SLACK_TOKEN"),
    ("stripe_live", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"), "REDACTED_STRIPE_LIVE"),
    ("stripe_test", re.compile(r"\bsk_test_[A-Za-z0-9]{16,}\b"), "REDACTED_STRIPE_TEST"),
    ("stripe_pk_live", re.compile(r"\bpk_live_[A-Za-z0-9]{16,}\b"), "REDACTED_STRIPE_PK_LIVE"),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "REDACTED_OPENAI_STYLE_KEY"),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b"), "REDACTED_ANTHROPIC_KEY"),
    ("xai_key", re.compile(r"\bxai-[A-Za-z0-9]{20,}\b"), "REDACTED_XAI_KEY"),
    ("vercel_token", re.compile(r"(?i)(vercel[_-]?token)\s*[=:]\s*['\"]?[A-Za-z0-9_]{20,}"), r"\1=REDACTED_VERCEL_TOKEN"),
    ("bearer", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.=]{20,}"), "Bearer REDACTED_BEARER"),
    ("private_key_block", re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z]*PRIVATE KEY-----"), "-----BEGIN PRIVATE KEY-----\nREDACTED_PRIVATE_KEY\n-----END PRIVATE KEY-----"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"), "REDACTED_JWT"),
    ("password_assign", re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]"), r"\1=REDACTED_PASSWORD"),
    ("api_key_assign", re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|private[_-]?key)\s*[=:]\s*['\"]?[^\s'\"#]{12,}"), r"\1=REDACTED_SECRET"),
    ("connection_string", re.compile(r"(?i)(postgres|mysql|mongodb|redis)://[^\s'\"<>]+"), r"REDACTED_DB_URL"),
    ("vca_token", re.compile(r"\bvca_[A-Za-z0-9]{20,}\b"), "REDACTED_VCA_TOKEN"),
]

# Residual forbidden after redaction (must not remain)
RESIDUAL_FORBIDDEN = [
    re.compile(r"\bsk_live_[A-Za-z0-9]{10,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{10,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{10,}\b"),
    re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]


@dataclass
class Finding:
    kind: str
    path: str
    detail: str


@dataclass
class PackReport:
    pack_id: str
    created_at: str
    ok: bool
    inbox: str
    sources: list[str] = field(default_factory=list)
    included_files: list[str] = field(default_factory=list)
    skipped_files: list[dict] = field(default_factory=list)
    denied: list[Finding] = field(default_factory=list)
    redactions: list[Finding] = field(default_factory=list)
    residuals: list[Finding] = field(default_factory=list)
    renames_applied: int = 0
    errors: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        d = asdict(self)
        return d


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def pack_id_slug(label: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", label).strip("-")[:40] or "pack"
    return f"pack_{ts}_{slug}"


def load_deny_patterns(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def load_token_map(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=>" not in line:
            continue
        left, right = line.split("=>", 1)
        left, right = left.strip(), right.strip()
        if left and right and left != right:
            pairs.append((left, right))
    # Longer keys first so nested names rename cleanly
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def repo_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def matches_deny(rel: str, name: str, patterns: Iterable[str]) -> str | None:
    candidates = {rel, name, f"**/{name}", rel.lstrip("./")}
    # Also try each path segment prefix
    parts = rel.split("/")
    for i in range(len(parts)):
        candidates.add("/".join(parts[: i + 1]))
        candidates.add("/".join(parts[: i + 1]) + "/**")
    for pat in patterns:
        for c in candidates:
            if fnmatch.fnmatch(c, pat) or fnmatch.fnmatch(c.lower(), pat.lower()):
                return pat
            # basename-only patterns
            if "/" not in pat.rstrip("*") and fnmatch.fnmatch(name, pat):
                return pat
    return None


def should_skip_binary(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    # Heuristic: null bytes in first 2k
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        if b"\x00" in chunk:
            return True
    except OSError:
        return True
    return False


def redact_text(text: str) -> tuple[str, list[str]]:
    hits: list[str] = []
    out = text
    for name, pattern, repl in SECRET_SPECS:
        new_out, n = pattern.subn(repl, out)
        if n:
            hits.append(f"{name}x{n}")
            out = new_out
    return out, hits


def apply_token_map(text: str, pairs: list[tuple[str, str]]) -> tuple[str, int]:
    count = 0
    out = text
    for src, dst in pairs:
        if src in out:
            n = out.count(src)
            out = out.replace(src, dst)
            count += n
    return out, count


def residual_secrets(text: str) -> list[str]:
    found: list[str] = []
    for pat in RESIDUAL_FORBIDDEN:
        m = pat.search(text)
        if m:
            found.append(m.group(0)[:48])
    return found


def collect_files(
    sources: list[Path],
    repo_root: Path,
    deny: list[str],
    max_file_bytes: int,
    max_files: int,
) -> tuple[list[Path], list[Finding], list[dict]]:
    denied: list[Finding] = []
    skipped: list[dict] = []
    files: list[Path] = []

    for src in sources:
        src = src.resolve()
        if not src.exists():
            denied.append(Finding("missing", str(src), "path does not exist"))
            continue

        if src.is_file():
            candidates = [src]
        else:
            candidates = [p for p in src.rglob("*") if p.is_file()]

        for path in candidates:
            rel = repo_rel(path, repo_root) if is_under(path, repo_root) else str(path)
            name = path.name
            hit = matches_deny(rel, name, deny)
            if hit:
                denied.append(Finding("deny_path", rel, f"matched deny pattern: {hit}"))
                continue
            if should_skip_binary(path):
                skipped.append({"path": rel, "reason": "binary_or_media"})
                continue
            try:
                size = path.stat().st_size
            except OSError as e:
                skipped.append({"path": rel, "reason": f"stat_error:{e}"})
                continue
            if size > max_file_bytes:
                skipped.append({"path": rel, "reason": f"too_large:{size}"})
                continue
            if size == 0:
                skipped.append({"path": rel, "reason": "empty"})
                continue
            files.append(path)
            if len(files) > max_files:
                denied.append(
                    Finding("limit", rel, f"exceeded max_files={max_files}")
                )
                return files, denied, skipped

    return files, denied, skipped


def write_pack(
    pack_dir: Path,
    pack_id: str,
    files: list[Path],
    repo_root: Path,
    token_pairs: list[tuple[str, str]],
    task_body: str,
    source_label: str,
    apply_renames: bool,
    report: PackReport,
) -> None:
    source_dir = pack_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    for path in files:
        rel = repo_rel(path, repo_root) if is_under(path, repo_root) else path.name
        # Flatten absolute outside-repo into source/_external/
        if not is_under(path, repo_root):
            dest_rel = Path("_external") / path.name
        else:
            dest_rel = Path(rel)
        dest = source_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            report.errors.append(f"read_failed:{rel}:{e}")
            continue

        redacted, hits = redact_text(raw)
        for h in hits:
            report.redactions.append(Finding("redact", rel, h))

        renames = 0
        if apply_renames and token_pairs:
            redacted, renames = apply_token_map(redacted, token_pairs)
            report.renames_applied += renames

        residuals = residual_secrets(redacted)
        if residuals:
            for r in residuals:
                report.residuals.append(Finding("residual_secret", rel, r))
            continue  # do not write unsafe content

        dest.write_text(redacted, encoding="utf-8")
        report.included_files.append(str(dest_rel).replace("\\", "/"))

    # Fail closed if residuals
    if report.residuals:
        report.ok = False
        report.errors.append("residual secrets after redaction — pack refused")
        return

    if not report.included_files:
        report.ok = False
        report.errors.append("no files included after filtering")
        return

    # TASK.md
    template = DEFAULT_TEMPLATE.read_text(encoding="utf-8") if DEFAULT_TEMPLATE.exists() else (
        "# Task\n\n{{TASK_BODY}}\n"
    )
    task_md = (
        template.replace("{{PACK_ID}}", pack_id)
        .replace("{{CREATED_AT}}", report.created_at)
        .replace("{{SOURCE_LABEL}}", source_label)
        .replace("{{TASK_BODY}}", task_body.strip() or "(No task body provided — inspect source/ and propose safe improvements.)")
    )
    (pack_dir / "TASK.md").write_text(task_md, encoding="utf-8")

    allowed = f"""# ALLOWED surface for pack `{pack_id}`

## You may
- Read `source/` in this pack
- Write deliverables under `~/Documents/kimi/workspace/_outbox_to_helm/{pack_id}/`
- Create notes, diffs, tests-as-text

## You may not
- Access `/Users/michaelhoch/hoch_agent_swarm` or any monorepo path
- Reconstruct `REDACTED_*` secrets
- Claim live production / payment / store state without evidence (you have none)

## Handoff complete when
- `_outbox_to_helm/{pack_id}/SUMMARY.md` exists
- Changes are proposed, not force-applied to HELM
"""
    (pack_dir / "ALLOWED.md").write_text(allowed, encoding="utf-8")

    outbox_hint = Path.home() / "Documents" / "kimi" / "workspace" / "_outbox_to_helm" / pack_id
    outbox_hint.mkdir(parents=True, exist_ok=True)
    (outbox_hint / "README.md").write_text(
        f"# Outbox for `{pack_id}`\n\nDrop SUMMARY.md, CHANGES/, RISKS.md here.\n",
        encoding="utf-8",
    )

    report.ok = True


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed, redacted Kimi handoff pack into Documents/kimi inbox."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to include (prefer monorepo-relative paths)",
    )
    parser.add_argument(
        "--task",
        "-t",
        default="",
        help="Task instructions for Kimi (or path to a .md file with @prefix: @file.md)",
    )
    parser.add_argument(
        "--task-file",
        default="",
        help="Path to a markdown file containing the task body",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Short label for pack id / source label",
    )
    parser.add_argument(
        "--inbox",
        default=str(DEFAULT_INBOX),
        help=f"Inbox directory (default: {DEFAULT_INBOX})",
    )
    parser.add_argument(
        "--deny-file",
        default=str(DEFAULT_DENY),
        help="Deny patterns file",
    )
    parser.add_argument(
        "--token-map",
        default=str(DEFAULT_TOKEN_MAP),
        help="Token rename map file",
    )
    parser.add_argument(
        "--no-rename",
        action="store_true",
        help="Skip soft IP token renames (still redacts secrets)",
    )
    parser.add_argument(
        "--max-file-kb",
        type=int,
        default=200,
        help="Max single file size in KB (default 200)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=80,
        help="Max files in pack (default 80)",
    )
    parser.add_argument(
        "--allow-denied",
        action="store_true",
        help="Do not fail if some inputs match deny list (those files still excluded)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report only; do not write pack",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Monorepo root for relative path labels",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    deny = load_deny_patterns(Path(args.deny_file))
    token_pairs = [] if args.no_rename else load_token_map(Path(args.token_map))
    inbox = Path(args.inbox).expanduser().resolve()

    # Resolve sources relative to repo root if needed
    sources: list[Path] = []
    for p in args.paths:
        path = Path(p).expanduser()
        if not path.is_absolute():
            cand = (repo_root / path).resolve()
            if cand.exists():
                path = cand
            else:
                path = path.resolve()
        else:
            path = path.resolve()
        sources.append(path)

    # Task body
    task_body = args.task
    if args.task_file:
        task_body = Path(args.task_file).expanduser().read_text(encoding="utf-8", errors="replace")
    elif task_body.startswith("@") and Path(task_body[1:]).expanduser().exists():
        task_body = Path(task_body[1:]).expanduser().read_text(encoding="utf-8", errors="replace")

    label = args.label or (sources[0].name if sources else "pack")
    pid = pack_id_slug(label)
    created = utc_now()
    report = PackReport(
        pack_id=pid,
        created_at=created,
        ok=False,
        inbox=str(inbox),
        sources=[str(s) for s in sources],
    )

    max_file_bytes = max(1, args.max_file_kb) * 1024
    files, denied, skipped = collect_files(
        sources,
        repo_root,
        deny,
        max_file_bytes=max_file_bytes,
        max_files=args.max_files,
    )
    report.denied = denied
    report.skipped_files = skipped

    # Fail closed if any *requested top-level* path is fully denied and nothing remains
    hard_deny = [d for d in denied if d.kind in ("deny_path", "missing", "limit")]
    if hard_deny and not args.allow_denied:
        # Only fail hard if we got zero files OR a missing path was requested
        if any(d.kind == "missing" for d in hard_deny) or not files:
            report.ok = False
            report.errors.append(
                "denied or missing paths with nothing safe to pack "
                "(use narrower paths, or --allow-denied only if intentional)"
            )
            print(json.dumps(report.to_json(), indent=2))
            print("\nFAIL: nothing safe to pack / hard deny", file=sys.stderr)
            return 1

    if not files:
        report.errors.append("no candidate files after deny/binary/size filters")
        print(json.dumps(report.to_json(), indent=2))
        print("\nFAIL: no files", file=sys.stderr)
        return 1

    if args.dry_run:
        # Simulate redaction stats
        for path in files:
            rel = repo_rel(path, repo_root) if is_under(path, repo_root) else path.name
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                report.errors.append(f"read_failed:{rel}:{e}")
                continue
            redacted, hits = redact_text(raw)
            for h in hits:
                report.redactions.append(Finding("redact", rel, h))
            if not args.no_rename and token_pairs:
                _, n = apply_token_map(redacted, token_pairs)
                report.renames_applied += n
            for r in residual_secrets(redacted):
                report.residuals.append(Finding("residual_secret", rel, r))
            report.included_files.append(rel)
        report.ok = not report.residuals and not report.errors
        print(json.dumps(report.to_json(), indent=2))
        print("\nDRY-RUN:", "OK" if report.ok else "FAIL")
        return 0 if report.ok else 1

    pack_dir = inbox / pid
    if pack_dir.exists():
        print(f"ERROR: pack dir already exists: {pack_dir}", file=sys.stderr)
        return 2
    pack_dir.mkdir(parents=True, exist_ok=False)

    try:
        write_pack(
            pack_dir=pack_dir,
            pack_id=pid,
            files=files,
            repo_root=repo_root,
            token_pairs=token_pairs,
            task_body=task_body,
            source_label=label,
            apply_renames=not args.no_rename,
            report=report,
        )

        if not report.ok:
            # Wipe incomplete / unsafe pack
            shutil.rmtree(pack_dir, ignore_errors=True)
            print(json.dumps(report.to_json(), indent=2))
            print("\nFAIL: pack refused (fail-closed)", file=sys.stderr)
            return 1

        # MANIFEST + SCAN_REPORT
        manifest = {
            "pack_id": pid,
            "created_at": created,
            "inbox": str(inbox),
            "outbox": str(Path.home() / "Documents/kimi/workspace/_outbox_to_helm" / pid),
            "source_label": label,
            "sources": report.sources,
            "file_count": len(report.included_files),
            "files": report.included_files,
            "renames_applied": report.renames_applied,
            "redaction_events": len(report.redactions),
            "policy": {
                "deny_file": str(args.deny_file),
                "token_map": str(args.token_map) if not args.no_rename else None,
                "max_file_kb": args.max_file_kb,
                "max_files": args.max_files,
            },
        }
        (pack_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        (pack_dir / "SCAN_REPORT.json").write_text(
            json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8"
        )

        # Optional tarball for easy share into Kimi chat
        tgz = inbox / f"{pid}.tgz"
        with tarfile.open(tgz, "w:gz") as tar:
            tar.add(pack_dir, arcname=pid)

        print(json.dumps(report.to_json(), indent=2))
        print(f"\nOK: pack written → {pack_dir}")
        print(f"OK: tarball      → {tgz}")
        print(f"OK: outbox       → {Path.home() / 'Documents/kimi/workspace/_outbox_to_helm' / pid}")
        print("\nNext: open Kimi on ~/Documents/kimi/workspace and point it at this pack.")
        return 0
    except Exception as e:
        shutil.rmtree(pack_dir, ignore_errors=True)
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
