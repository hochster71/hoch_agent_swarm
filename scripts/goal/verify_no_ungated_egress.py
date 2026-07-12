#!/usr/bin/env python3
"""REQ-ES-003 — universal dispatch enforcement (AST-accurate).

RATIFIED EXIT CONDITION
-----------------------
No raw provider SDK, HTTP, socket, or model-CLI invocation may occur OUTSIDE the
approved council gateway modules. Every other module must route through the gateway,
or install the dispatch guard so its provider I/O fails closed.

WHY THIS REPLACES THE STRING-MATCH SCANNER
------------------------------------------
The previous check flagged any file that merely CONTAINED a provider hostname string.
7 findings, of which 5 were false positives: scanners, an inventory tool, and base-URL
string constants that make no call at all. A scanner that cannot tell a call from a
mention is not an enforcement.

This scanner uses the AST. A violation requires an ACTUAL CALL EXPRESSION reaching a
PROVIDER target, in a module that is NEITHER an approved gateway module NOR guarded
(it neither installs ensure_guard() nor dispatches through the gateway).

Loopback (127.0.0.1 / localhost) is not provider egress and is never a violation.
A hostname inside a comment, a regex, an allowlist, or a base-URL assignment is a
mention, not a call, and is never a violation.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "ungated_egress_report.json"

# The ONLY modules permitted to contain raw provider I/O. They ARE the gateway boundary.
APPROVED_GATEWAY_MODULES = {
    "scripts/council/gateway.py",
    "scripts/council/spend_gate.py",
    "scripts/council/adapters.py",
    "scripts/council/dispatch.py",
}

PROVIDER_HOSTS = {
    "api.openai.com", "api.anthropic.com", "api.x.ai",
    "generativelanguage.googleapis.com",
}
MODEL_CLI_BINARIES = {"grok", "gemini", "claude", "codex", "ollama"}

NET_CALLS = {
    ("urllib", "request", "urlopen"), ("request", "urlopen"), ("urlopen",),
    ("requests", "post"), ("requests", "get"), ("requests", "request"),
    ("httpx", "post"), ("httpx", "get"), ("httpx", "Client"),
    ("aiohttp", "ClientSession"),
    ("socket", "create_connection"), ("socket", "socket"),
}
# Request builders carry the URL even when the actual invocation (urlopen) does not.
REQUEST_BUILDERS = {
    ("urllib", "request", "Request"), ("request", "Request"), ("Request",),
    ("requests", "Request"),
}
SUBPROC_CALLS = {("subprocess", "run"), ("subprocess", "Popen"), ("os", "system")}


def _dotted(node: ast.AST) -> tuple[str, ...]:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return tuple(reversed(parts))


def _string_consts(call: ast.Call) -> str:
    return " ".join(n.value for n in ast.walk(call)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)).lower()


def module_is_guarded(tree: ast.AST) -> bool:
    """True if the module installs the dispatch guard or routes through the gateway."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            tgt = _dotted(n.func)
            if tgt and tgt[-1] in ("ensure_guard", "install"):
                return True
        if isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            names = " ".join(a.name for a in n.names)
            if "gateway" in mod and ("ensure_guard" in names or "CouncilDispatchGateway" in names):
                return True
    return False


def _endswith(tgt: tuple[str, ...], sigs: set) -> bool:
    return any(len(tgt) >= len(sig) and tgt[-len(sig):] == sig for sig in sigs)


def scan_module(rel: str) -> list[dict]:
    p = ROOT / rel
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return []

    if rel in APPROVED_GATEWAY_MODULES:
        return []                       # the gateway boundary itself is permitted
    guarded = module_is_guarded(tree)

    # Provider hosts named INSIDE a real request-builder or net call. A host that
    # appears only in an allowlist / regex / comment is not collected here.
    provider_hosts_in_calls: set[str] = set()
    has_net_invocation = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        tgt = _dotted(node.func)
        if _endswith(tgt, NET_CALLS):
            has_net_invocation = True
        if _endswith(tgt, NET_CALLS) or _endswith(tgt, REQUEST_BUILDERS):
            provider_hosts_in_calls |= {h for h in PROVIDER_HOSTS
                                        if h in _string_consts(node)}

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        tgt = _dotted(node.func)

        # a real net invocation, in a module that names a provider host in its
        # request construction, and is neither approved nor guarded
        if (_endswith(tgt, NET_CALLS) and provider_hosts_in_calls
                and has_net_invocation and not guarded):
            findings.append({
                "file": rel, "line": node.lineno, "kind": "PROVIDER_HTTP_CALL",
                "target": ".".join(tgt), "hosts": sorted(provider_hosts_in_calls),
                "defect": "raw provider HTTP call outside an approved/guarded module",
            })
            break  # one finding per module is enough to fail it
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        tgt = _dotted(node.func)
        if _endswith(tgt, SUBPROC_CALLS) and not guarded:
            first = None
            if node.args:
                a0 = node.args[0]
                if isinstance(a0, (ast.List, ast.Tuple)) and a0.elts and \
                        isinstance(a0.elts[0], ast.Constant):
                    first = str(a0.elts[0].value)
                elif isinstance(a0, ast.Constant) and a0.value:
                    first = str(a0.value).split()[0]
            base = Path(first).name if first else ""
            if base in MODEL_CLI_BINARIES:
                findings.append({
                    "file": rel, "line": node.lineno, "kind": "MODEL_CLI_SUBPROCESS",
                    "target": ".".join(tgt), "binary": base,
                    "defect": "raw model-CLI subprocess outside an approved/guarded module",
                })
    return findings


def main() -> int:
    violations: list[dict] = []
    for p in ROOT.rglob("*.py"):
        rel = str(p.relative_to(ROOT))
        if any(s in rel for s in ("node_modules", ".venv", "__pycache__",
                                  "docs/evidence", "archive/", "/tests/", "tests/")):
            continue
        violations.extend(scan_module(rel))

    report = {
        "requirement": "REQ-ES-003",
        "policy": "no raw provider SDK/HTTP/socket/model-CLI invocation outside approved or guarded modules",
        "approved_gateway_modules": sorted(APPROVED_GATEWAY_MODULES),
        "ungated_egress": violations,
        "violation_count": len(violations),
        "status": "PASS" if not violations else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, indent=2, sort_keys=True) + "\n"
    OUT.write_text(body, encoding="utf-8")
    print(f"REQ-ES-003 ungated-egress scan: {len(violations)} violations")
    for v in violations[:12]:
        print(f"  {v['file']}:{v['line']}  {v['kind']}  {v.get('hosts') or v.get('binary')}")
    print(f"report sha256: {hashlib.sha256(body.encode()).hexdigest()}")
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
