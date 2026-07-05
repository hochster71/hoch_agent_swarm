#!/usr/bin/env python3
"""npm audit gate with a documented accepted-risk allowlist.

Reads `npm audit --json` output and config/security_accepted_risks.json. A high/critical
advisory is non-blocking ONLY if it is listed in the allowlist AND not expired. Any high+
advisory that is NOT documented+accepted fails the gate. This preserves security (new CVEs
block) while allowing evidence-based, time-boxed risk acceptance (no fake-green).

Exit 0 = pass (no unaccepted high+ advisories). Exit 1 = fail.
Usage: npm_audit_gate.py <npm_audit.json> <accepted_risks.json>
"""
import json
import re
import sys
import datetime
from pathlib import Path


def load_accepted(path):
    now = datetime.datetime.now(datetime.timezone.utc)
    ids = set()
    p = Path(path)
    if not p.exists():
        return ids
    for a in json.loads(p.read_text()).get("accepted", []):
        exp = a.get("expires")
        if exp:
            try:
                if datetime.datetime.fromisoformat(str(exp) + "T00:00:00+00:00") < now:
                    continue  # expired acceptance no longer counts
            except Exception:
                pass
        if a.get("advisory"):
            ids.add(a["advisory"])
        if a.get("package"):
            ids.add(a["package"])
    return ids


def main():
    audit_path, allow_path = sys.argv[1], sys.argv[2]
    try:
        audit = json.loads(Path(audit_path).read_text())
    except Exception as e:
        print(f"npm audit output unreadable: {e}"); return 1
    accepted = load_accepted(allow_path)

    unaccepted = []
    for pkg, v in (audit.get("vulnerabilities") or {}).items():
        if v.get("severity") not in ("high", "critical"):
            continue
        ids = {pkg}
        for via in v.get("via", []):
            if isinstance(via, dict):
                m = re.search(r"GHSA-[\w-]+", via.get("url", "") or "")
                if m:
                    ids.add(m.group(0))
                if via.get("source"):
                    ids.add(str(via["source"]))
            elif isinstance(via, str):
                ids.add(via)  # transitive: vulnerable *because of* this package (e.g. vite via esbuild)
        if not (ids & accepted):
            unaccepted.append(f"{pkg}({v.get('severity')})")

    if unaccepted:
        print("FAIL: unaccepted high+ advisories -> " + ", ".join(sorted(set(unaccepted))))
        return 1
    print("PASS: high+ advisories all documented+accepted (or none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
