"""CYB-001 — dependency metadata must not misrepresent the executing environment.

METADATA != EXECUTION (founder, 2026-07-21). The unifying form of a defect this project
has now hit five times:

    runtime truth      != dashboard state
    observation        != inference
    presence           != capability
    lockfile           != executing environment
    CVE severity       != exploitability in this deployment

All are the same error: treating a DESCRIPTIVE ARTIFACT as the PROPERTY it describes.

The specific instance guarded here: `dummy_mcp` is a local resolution stub with no code.
It previously declared version "1.28.2" — an upstream RELEASE number — so `uv.lock`
recorded `mcp 1.28.2`, which reads as "patched" to any scanner. Nothing was patched.
The real `mcp` on this machine is 1.23.3 with the vulnerable transports present.

These tests fail if the stub is ever again given a version that could be mistaken for a
real release, or if it silently acquires dependencies or code.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

STUB = ROOT / "dummy_mcp" / "pyproject.toml"


@pytest.fixture
def meta():
    if not STUB.exists():
        pytest.skip("dummy_mcp stub removed — preferred outcome, nothing to guard")
    return tomllib.loads(STUB.read_text())["project"]


def test_stub_version_is_a_LOCAL_version_not_a_release(meta):
    """THE guard. A local version identifier (PEP 440 '+local') can never be confused
    with an upstream release and will not satisfy a >= constraint on a patched version."""
    v = meta["version"]
    assert "+" in v, f"stub version {v!r} has no local identifier — it can impersonate a release"
    assert v.split("+")[0] == "0.0.0", f"stub base version {v!r} must be 0.0.0"


def test_stub_version_does_not_resemble_any_real_mcp_release(meta):
    """1.28.2 was the exact shape of the problem: plausible, current, and patched-looking."""
    v = meta["version"]
    assert not re.match(r"^\d+\.\d+\.\d+$", v), (
        f"stub version {v!r} is a bare semver — indistinguishable from an upstream release")


def test_stub_description_states_it_is_not_upstream(meta):
    """Metadata is what a scanner and a hurried engineer read. It must say what this is."""
    d = meta["description"].upper()
    assert "STUB" in d
    assert "NOT" in d and "UPSTREAM" in d


def test_stub_declares_no_dependencies(meta):
    """A stub that grows a dependency graph stops being inert and starts being a
    supply-chain surface that nothing audits."""
    assert meta.get("dependencies") == []


def test_stub_ships_no_functional_code():
    """If it ever contains real code it is no longer a resolution placeholder, and the
    'no functionality' claim in its own metadata becomes false."""
    src = ROOT / "dummy_mcp" / "src" / "mcp"
    if not src.exists():
        return
    body = "".join(
        p.read_text() for p in src.rglob("*.py")
    )
    stripped = re.sub(r'("""|\'\'\')(.|\n)*?\1', "", body)      # drop docstrings
    stripped = re.sub(r"#.*", "", stripped)                      # drop comments
    code = [ln for ln in stripped.splitlines() if ln.strip()]
    assert len(code) < 10, (
        f"stub carries {len(code)} lines of executable code — it is no longer a placeholder")


# Dormant-lane imports that exist ONLY to read mcp.__version__ for a report. Enumerated
# explicitly so that converting one into real usage (mcp.Client(...), a transport, a
# server) breaks the allowlist and fails the test.
PERMITTED_VERSION_INTROSPECTION = {
    "src/hoch_agent_swarm/run_report.py": "_mcp_stub_version",
    "src/hoch_agent_swarm/release_candidate.py": "_mcp_version",
}
RUNTIME_DIRS = ("backend", "scripts")   # the live HELM runtime — must stay at zero


def _mcp_import_sites(root: Path):
    """AST, not grep. The original claim here was 'zero imports', produced by a grep
    anchored on '^import mcp' plus a shell glob that silently matched nothing. Two
    indented imports inside functions were invisible to it, and this test is what
    falsified the claim. SEARCH RESULTS != PROGRAM BEHAVIOUR."""
    import ast
    out = []
    for d in root.iterdir():
        if d.name not in RUNTIME_DIRS + ("src",) or not d.is_dir():
            continue
        for f in d.rglob("*.py"):
            if ".venv" in str(f) or "node_modules" in str(f):
                continue
            try:
                tree = ast.parse(f.read_text(errors="ignore"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [node.module or ""]
                if any(m == "mcp" or m.startswith("mcp.") for m in mods):
                    out.append((str(f.relative_to(root)), node.lineno))
    return out


def test_HELM_RUNTIME_has_zero_mcp_imports():
    """THE invariant. backend/ and scripts/ are the live runtime. A single import there
    puts the vulnerable transports one call away and makes the stub a shadowing hazard:
    resolution order decides whether real or stub loads, and uv.lock says 'patched'
    either way."""
    live = [s for s in _mcp_import_sites(ROOT)
            if s[0].split("/")[0] in RUNTIME_DIRS]
    assert not live, (
        f"HELM runtime now imports mcp at {live} — DELETE dummy_mcp and depend on "
        "upstream >=1.28.1. A stub shadowing a security-relevant package is worse "
        "than no stub.")


def test_dormant_mcp_imports_match_the_permitted_allowlist():
    """Dormant-lane version introspection is permitted but ENUMERATED. If a new file
    starts importing mcp, or an existing one grows beyond reading __version__, this
    fails — which is the point."""
    found = {s[0] for s in _mcp_import_sites(ROOT)}
    unexpected = found - set(PERMITTED_VERSION_INTROSPECTION)
    assert not unexpected, (
        f"unenumerated mcp import(s): {sorted(unexpected)} — if this is real usage, "
        "the stub must go; if it is more version reporting, add it here deliberately.")


def test_permitted_sites_still_only_read_a_version_string():
    """Behaviour, not syntax. `import mcp` is fine; `mcp.Client(...)` is not."""
    import ast
    for rel, fname in PERMITTED_VERSION_INTROSPECTION.items():
        f = ROOT / rel
        if not f.exists():
            continue
        tree = ast.parse(f.read_text(errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == fname:
                attrs = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
                calls = {getattr(n.func, "attr", None) for n in ast.walk(node)
                         if isinstance(n, ast.Call)}
                assert attrs <= {"__version__", "get"}, (
                    f"{rel}::{fname} touches mcp attributes beyond __version__: {attrs}")
                assert not (calls & {"Client", "ClientSession", "Server", "connect"}), (
                    f"{rel}::{fname} now CALLS into mcp: {calls} — this is real usage, "
                    "not version reporting. The stub must be removed.")
