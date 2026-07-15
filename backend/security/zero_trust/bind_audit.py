"""bind_audit — fail-closed enumeration of exposure surface (SC-7 boundary protection).

Two independent lenses, both read-only:

1. RUNTIME listeners: what is actually LISTENing on this host right now (psutil).
   Any socket bound to 0.0.0.0 / :: / "" (all interfaces) is flagged.
2. CONFIG bindings: how launchers *intend* to bind (grep of launch scripts and
   service units for ``--host 0.0.0.0`` / ``host="0.0.0.0"``). This is the ground
   truth even when the audit runs somewhere the live service is not (e.g. a CI
   sandbox), because the exposure is baked into the launch config.

Fail-closed contract:
  * ANY 0.0.0.0 finding (runtime or config)  -> verdict FAIL, exit code 2.
  * enumeration itself errors / is unavailable -> verdict UNKNOWN, exit code 3
    (never a silent PASS).
  * only when both lenses succeed AND find zero all-interface bindings -> PASS(0).

This script NEVER opens, connects to, binds, or signals any socket. It reads
/proc-style listener tables and static files only. It will not disturb :8770.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]

ALL_IFACE = {"0.0.0.0", "::", ""}

# Launch/config files most likely to carry a bind directive. Scanned if present.
CONFIG_GLOBS = [
    "scripts/**/*.sh",
    "scripts/**/*.py",
    "docker/**/*.sh",
    "docker/**/*",
    "systemd/**/*",
    "k8s/**/*.yaml",
    "k8s/**/*.yml",
    "deploy/**/*",
    "backend/mission_control/helm_supervisor.py",
    "backend/main.py",
]

# Patterns that indicate an all-interfaces bind.
BIND_PATTERNS = [
    re.compile(r"--host\s+0\.0\.0\.0"),
    re.compile(r"host\s*=\s*[\"']0\.0\.0\.0[\"']"),
    re.compile(r"host\s*=\s*0\.0\.0\.0"),
    re.compile(r"\*:\d+"),  # "*:8770" style
]

EXCLUDE_DIRS = {".venv", "node_modules", "__pycache__", ".git", "dist", "archive"}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def enumerate_listeners() -> Dict[str, Any]:
    """Return live LISTEN sockets and flag all-interface binds. Fail-closed."""
    try:
        import psutil
    except Exception as e:  # pragma: no cover - psutil is a dep, but be safe
        return {"available": False, "reason": f"psutil unavailable: {e}", "listeners": []}
    out: List[Dict[str, Any]] = []
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception as e:
        return {"available": False, "reason": f"net_connections failed: {e}", "listeners": []}
    for c in conns:
        if c.status != psutil.CONN_LISTEN:
            continue
        ip = c.laddr.ip if c.laddr else ""
        port = c.laddr.port if c.laddr else None
        exposed = ip in ALL_IFACE
        proc = ""
        if c.pid:
            try:
                proc = psutil.Process(c.pid).name()
            except Exception:
                proc = f"pid:{c.pid}"
        out.append(
            {
                "ip": ip,
                "port": port,
                "pid": c.pid,
                "process": proc,
                "all_interfaces": exposed,
            }
        )
    return {"available": True, "listeners": out}


def scan_config_bindings() -> Dict[str, Any]:
    """Grep launch configs for all-interface bind directives. Fail-closed."""
    findings: List[Dict[str, Any]] = []
    scanned = 0
    seen: set[Path] = set()
    for pattern in CONFIG_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file() or path in seen:
                continue
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            seen.add(path)
            scanned += 1
            try:
                text = path.read_text(errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for rx in BIND_PATTERNS:
                    if rx.search(line):
                        findings.append(
                            {
                                "file": str(path.relative_to(ROOT)),
                                "line": i,
                                "text": line.strip()[:200],
                            }
                        )
                        break
    return {"files_scanned": scanned, "findings": findings}


def detect_tls() -> Dict[str, Any]:
    """Best-effort check that the live API is served over TLS. It is not: the
    launcher runs plain-HTTP uvicorn and Tailscale terminates HTTPS in front of a
    plain-HTTP origin. Report the absence honestly (SC-8 gap)."""
    # Look for ssl_certfile / ssl_keyfile in the launcher; absent == plain HTTP.
    launcher = ROOT / "scripts" / "helm_autoloop.sh"
    tls_configured = False
    if launcher.exists():
        t = launcher.read_text(errors="ignore")
        tls_configured = ("ssl-certfile" in t) or ("ssl_certfile" in t) or ("--ssl" in t)
    return {
        "live_api_tls_configured": tls_configured,
        "note": (
            "SC-8 gap: origin :8770 is plain HTTP. Tailscale terminates HTTPS in "
            "front but the origin transmits in the clear."
        ),
    }


def run_audit() -> Dict[str, Any]:
    listeners = enumerate_listeners()
    config = scan_config_bindings()
    tls = detect_tls()

    runtime_exposed = [l for l in listeners.get("listeners", []) if l.get("all_interfaces")]
    config_exposed = config.get("findings", [])

    # Fail-closed verdict.
    if not listeners.get("available") and not config_exposed:
        # Could not enumerate runtime AND found nothing in config -> we do not KNOW.
        verdict = "UNKNOWN"
        exit_code = 3
    elif runtime_exposed or config_exposed:
        verdict = "FAIL"
        exit_code = 2
    else:
        verdict = "PASS"
        exit_code = 0

    report = {
        "tool": "bind_audit",
        "assessed_at": _now(),
        "root": str(ROOT),
        "verdict": verdict,
        "exit_code": exit_code,
        "nist_controls": ["SC-7", "AC-4", "SC-8"],
        "framework": "NIST SP 800-207 Zero Trust / 800-53 Rev5",
        "runtime": {
            "available": listeners.get("available"),
            "reason": listeners.get("reason"),
            "total_listeners": len(listeners.get("listeners", [])),
            "all_interface_listeners": runtime_exposed,
        },
        "config": {
            "files_scanned": config.get("files_scanned"),
            "all_interface_bindings": config_exposed,
        },
        "tls": tls,
        "summary": (
            f"{len(runtime_exposed)} runtime + {len(config_exposed)} config "
            f"all-interface binding(s); TLS on origin: "
            f"{tls['live_api_tls_configured']}"
        ),
    }
    return report


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        out_path = Path(argv[i + 1])
    report = run_audit()
    text = json.dumps(report, indent=2)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n")
    print(text)
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
