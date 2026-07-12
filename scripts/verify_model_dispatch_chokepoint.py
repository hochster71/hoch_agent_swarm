#!/usr/bin/env python3
"""H1D.7 static enforcement: model-dispatch primitives must not bypass the gateway.

Fails non-zero when model-dispatch code outside approved modules contains
prohibited primitives (direct model-domain URLs with HTTP clients, provider
SDK clients, model CLI subprocesses).

Documented exceptions are path-specific and listed in APPROVED_EXCEPTIONS.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Modules permitted to perform model I/O (gateway + its CLI transport).
APPROVED_MODULES = {
    "scripts/council/gateway.py",
    "scripts/council/spend_gate.py",
}

# Path-specific exceptions: (relative_path, pattern_name, reason)
APPROVED_EXCEPTIONS: list[tuple[str, str, str]] = [
    (
        "scripts/prompt_brain/model_adapters.py",
        "urllib_import",
        "Loopback health_check GET only; execute() routes through gateway",
    ),
    (
        "scripts/prompt_brain/model_adapters.py",
        "urlopen",
        "Loopback health_check GET for LM Studio / Ollama tags only",
    ),
    (
        "scripts/prompt_brain/model_adapters.py",
        "api.openai.com",
        "Endpoint identity string / GatewayRequest endpoint field only; no direct POST",
    ),
    (
        "scripts/prompt_brain/model_adapters.py",
        "api.anthropic.com",
        "Endpoint identity string / GatewayRequest endpoint field only; no direct POST",
    ),
    (
        "scripts/council/adapters.py",
        "urllib_import",
        "Legacy H1B harness with separate founder egress ticket; not H1D router path",
    ),
    (
        "scripts/council/adapters.py",
        "urlopen",
        "Legacy H1B harness behind open_external_egress founder ticket",
    ),
    (
        "scripts/council/dispatch.py",
        "model_cli_name",
        "Adapter argv builders only; spawn is gateway-only",
    ),
    (
        "tests/",
        "any",
        "Tests may seed bypass fixtures and assert refusal",
    ),
    (
        "scripts/verify_model_dispatch_chokepoint.py",
        "any",
        "Scanner itself",
    ),
    (
        "scripts/council/inventory_outbound_paths.py",
        "any",
        "Inventory tool",
    ),
]

PROHIBITED = [
    ("urllib_import", re.compile(r"^\s*(import urllib|from urllib)"), "model_dispatch"),
    ("urlopen", re.compile(r"urllib\.request\.urlopen|urlopen\s*\("), "model_dispatch"),
    ("requests", re.compile(r"\brequests\.(get|post|put|delete|request|Session)\b"), "model_dispatch"),
    ("httpx", re.compile(r"\bhttpx\.(get|post|Client|AsyncClient)\b"), "model_dispatch"),
    ("openai_sdk", re.compile(r"\bopenai\.(OpenAI|AzureOpenAI)\b|from openai import"), "model_dispatch"),
    ("anthropic_sdk", re.compile(r"\banthropic\.(Anthropic)\b|from anthropic import"), "model_dispatch"),
    ("api.openai.com", re.compile(r"api\.openai\.com"), "model_domain"),
    ("api.anthropic.com", re.compile(r"api\.anthropic\.com"), "model_domain"),
    (
        "subprocess_model_cli",
        re.compile(
            r"""subprocess\.(run|Popen|call|check_output)\s*\(\s*\[?\s*['\"](?:grok|gemini|ollama|claude)['\"]"""
        ),
        "model_cli",
    ),
    (
        "model_cli_name",
        re.compile(r"""['\"](?:grok|gemini|ollama|claude)['\"]\s*,\s*['\"]-p['\"]"""),
        "model_cli",
    ),
]

# H1D.7 primary surfaces: council dispatch path + prompt_brain adapters.
# Legacy backend model mesh is inventoried separately and listed as documented
# exceptions until a later unification milestone (not silent).
DISPATCH_GLOBS = [
    "scripts/prompt_brain/**/*.py",
    "scripts/council/**/*.py",
]

# Legacy backend model paths — must remain explicitly excepted (not invisible).
LEGACY_BACKEND_MODEL_GLOBS = [
    "backend/**/*adapter*.py",
    "backend/**/model_*.py",
    "backend/brain/model_router.py",
]


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        return str(p)


def _is_approved_module(rel: str) -> bool:
    return rel in APPROVED_MODULES


def _exception_allows(rel: str, pattern_name: str) -> bool:
    for path_prefix, pname, _reason in APPROVED_EXCEPTIONS:
        if path_prefix.endswith("/"):
            if not rel.startswith(path_prefix):
                continue
        elif rel != path_prefix and not rel.startswith(path_prefix.rstrip("/") + "/"):
            if rel != path_prefix:
                continue
        if pname == "any" or pname == pattern_name:
            return True
    return False


def _has_direct_openai_post(text: str) -> bool:
    """Detect the historical OpenAIAdapter direct POST bypass."""
    if "api.openai.com" not in text:
        return False
    if "urlopen" in text and "chat/completions" in text:
        # After H1D.7, execute routes via gateway — residual strings without urlopen+chat are OK
        # Flag only if urlopen call site still near chat/completions
        for i, line in enumerate(text.splitlines()):
            if "chat/completions" in line and ("http" in line or "openai" in line):
                # look nearby for urlopen
                window = "\n".join(text.splitlines()[max(0, i - 5) : i + 8])
                if "urlopen" in window and "GatewayRequest" not in window:
                    return True
    return False


def scan(seed_bypass_path: Path | None = None) -> dict:
    findings: list[dict] = []
    legacy_notes: list[dict] = []
    files: list[Path] = []
    for g in DISPATCH_GLOBS:
        files.extend(ROOT.glob(g))
    if seed_bypass_path and seed_bypass_path.exists():
        files.append(seed_bypass_path)

    seen = set()
    for path in sorted(set(files)):
        if not path.is_file() or path.suffix != ".py":
            continue
        rel = _rel(path)
        if rel in seen:
            continue
        seen.add(rel)
        if "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")

        if _is_approved_module(rel):
            continue

        # Hard check: residual direct OpenAI POST
        if _has_direct_openai_post(text) and not _exception_allows(rel, "api.openai.com"):
            findings.append(
                {
                    "file": rel,
                    "line": 0,
                    "pattern": "direct_openai_post",
                    "snippet": "api.openai.com + urlopen + chat/completions",
                    "severity": "violation",
                }
            )

        for line_no, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for pname, cre, _kind in PROHIBITED:
                if not cre.search(line):
                    continue
                if _exception_allows(rel, pname):
                    continue
                findings.append(
                    {
                        "file": rel,
                        "line": line_no,
                        "pattern": pname,
                        "snippet": line.strip()[:160],
                        "severity": "violation",
                    }
                )

    # Inventory legacy backend model paths (do not auto-PASS them away)
    for g in LEGACY_BACKEND_MODEL_GLOBS:
        for path in ROOT.glob(g):
            if not path.is_file() or path.suffix != ".py":
                continue
            rel = _rel(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(
                x in text
                for x in (
                    "urllib.request",
                    "requests.",
                    "httpx.",
                    "api.openai.com",
                    "subprocess",
                )
            ):
                legacy_notes.append(
                    {
                        "file": rel,
                        "classification": "legacy_backend_model_mesh",
                        "remediation_status": "documented_exception_pending_unification",
                        "note": "Not on H1D council path; must not gain new frontier POSTs without gateway",
                    }
                )

    return {
        "schema": "h1d7-chokepoint-scan-v1",
        "approved_modules": sorted(APPROVED_MODULES),
        "exception_count": len(APPROVED_EXCEPTIONS),
        "findings": findings,
        "violation_count": len(findings),
        "legacy_backend_notes": legacy_notes,
        "status": "PASS" if not findings else "FAIL",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--seed-bypass", type=Path, default=None,
                    help="Optional file path that should be flagged (self-test)")
    ap.add_argument("--expect-fail", action="store_true",
                    help="Invert exit code (for seeded-bypass self-test)")
    args = ap.parse_args()
    result = scan(seed_bypass_path=args.seed_bypass)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"H1D.7 chokepoint scan: {result['status']} "
              f"({result['violation_count']} violations)")
        for f in result["findings"][:50]:
            print(f"  {f['file']}:{f['line']} [{f['pattern']}] {f['snippet']}")
        if result["violation_count"] > 50:
            print(f"  ... {result['violation_count'] - 50} more")
    failed = result["status"] != "PASS"
    if args.expect_fail:
        return 0 if failed else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
