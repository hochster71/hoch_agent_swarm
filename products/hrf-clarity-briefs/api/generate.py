"""api/generate.py — HRF Clarity Briefs delivery route (Vercel Python function).

An entitled buyer POSTs a request (token + topic + sources + drafted claims) and
receives the assembled, linter-validated brief. This is the "request/delivery"
half of the loop: the JS webhook grants an entitlement token; this route consumes
it via the existing Python gate and runs the real engine.

Contract (POST JSON):
    {
      "token": "<entitlement token from the success page>",
      "topic": "…",
      "sources": [ {id,title,url,retrieved_at,text}, … ],
      "claims":  [ {text, citations:[{source_id,quote}]}, … ],
      "uncertainty": [ "…", … ]         # optional; auto-seeded if omitted
    }

Responses:
    200 { html, json, coverage_pct }   — brief rendered (credit consumed)
    400 { error }                      — bad JSON / missing topic
    402 { error }                      — not entitled -> go to checkout
    422 { error, summary }             — brief failed the citation linter (fail-closed)

HONESTY: this route VERIFIES user-provided sources + drafted claims (the engine's
real moat). Live source-gathering and LLM claim-composition are the documented
integration points still open (see README) — until they are wired, the caller
supplies the sources/claims and the engine polices them.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Make the sibling `engine/` package importable regardless of cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.schemas import request_from_dict  # noqa: E402
from engine.engine import generate_brief, BriefLintError  # noqa: E402
from engine.assembler import assemble_html  # noqa: E402
from engine.entitlement import EntitlementStore, EntitlementError  # noqa: E402


def build_response(body: dict):
    """Pure core (also unit-tested directly): returns (status_code, payload)."""
    token = (body or {}).get("token")
    if not token:
        return 402, {
            "error": "not_entitled",
            "message": "Missing entitlement token. Complete checkout, then redeem "
            "the token from your success page.",
        }

    if not (body.get("topic") or "").strip():
        return 400, {"error": "bad_request", "message": "A 'topic' is required."}

    try:
        request = request_from_dict(body)
    except (KeyError, TypeError, ValueError) as e:
        return 400, {"error": "bad_request", "message": f"Malformed request: {e}"}

    store = EntitlementStore()  # reads HRF_ENTITLEMENTS_PATH — same file the webhook writes
    try:
        brief = generate_brief(request, entitlement_token=token, entitlement_store=store)
    except EntitlementError:
        return 402, {
            "error": "not_entitled",
            "message": "This token is not entitled (unknown, unpaid, or out of "
            "credits). Buy a brief to continue.",
        }
    except BriefLintError as e:
        # Fail-closed: no brief is rendered when a claim is uncited/ungrounded.
        return 422, {
            "error": "lint_failed",
            "message": "The brief failed the citation-coverage check and was not "
            "rendered (every claim must cite a source, and every quote must appear "
            "verbatim in that source).",
            "summary": e.result.summary(),
        }

    return 200, {
        "coverage_pct": brief.coverage_pct,
        "html": assemble_html(brief),
        "json": brief.to_dict(),
    }


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):  # noqa: N802 (Vercel/BaseHTTPRequestHandler convention)
        try:
            length = int(self.headers.get("content-length") or 0)
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
            if not isinstance(body, dict):
                raise ValueError("body must be a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            return self._send(400, {"error": "bad_json", "message": f"Invalid JSON: {e}"})

        status, payload = build_response(body)
        self._send(status, payload)

    def do_GET(self):  # noqa: N802
        self._send(405, {"error": "method_not_allowed", "message": "Use POST."})
