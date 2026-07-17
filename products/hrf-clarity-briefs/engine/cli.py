"""Command-line runner for the Clarity Briefs engine.

Usage:
    python -m engine.cli --request examples/request.sample.json --out out/
    python -m engine.cli --request examples/request.sample.json --out out/ \
        --token tok_demo --entitlements examples/entitlements.sample.json

Reads a request JSON (topic + sources + drafted claims + uncertainty), runs the
engine (which fails closed via the citation-coverage linter), and writes
brief_<slug>_<UTC>.{md,html,json} to --out. On a lint failure it prints the
offending claims and exits non-zero — no brief is written. (fail-closed)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

from .schemas import request_from_dict
from .engine import generate_brief, BriefLintError
from .assembler import assemble_markdown, assemble_html, assemble_json
from .entitlement import EntitlementStore, EntitlementError


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "brief")[:48]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate a cited Clarity Brief.")
    p.add_argument("--request", required=True, help="path to request JSON")
    p.add_argument("--out", default="out", help="output directory")
    p.add_argument("--token", default=None, help="entitlement token (optional)")
    p.add_argument("--entitlements", default=None,
                   help="path to entitlements JSON store (optional)")
    args = p.parse_args(argv)

    with open(args.request, "r", encoding="utf-8") as f:
        request = request_from_dict(json.load(f))

    store = EntitlementStore(args.entitlements) if args.entitlements else None

    try:
        brief = generate_brief(
            request,
            entitlement_token=args.token,
            entitlement_store=store,
        )
    except EntitlementError as e:
        print(f"[ENTITLEMENT DENIED] {e}", file=sys.stderr)
        return 2
    except BriefLintError as e:
        print("[LINT FAILED] brief not rendered (fail-closed):", file=sys.stderr)
        print(e.result.summary(), file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"brief_{_slug(brief.topic)}_{stamp}"
    md_path = os.path.join(args.out, base + ".md")
    html_path = os.path.join(args.out, base + ".html")
    json_path = os.path.join(args.out, base + ".json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(assemble_markdown(brief))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(assemble_html(brief))
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(assemble_json(brief))

    print(f"[OK] coverage={brief.coverage_pct:.0f}% -> {md_path}")
    print(f"          {html_path}")
    print(f"          {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
