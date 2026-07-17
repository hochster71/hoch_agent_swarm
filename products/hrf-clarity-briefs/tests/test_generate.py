"""Tests for the delivery route core (api/generate.py :: build_response).

Proves the request/delivery half of the loop, using the same entitlement store
the webhook writes:
  * un-entitled token           -> 402 (go to checkout)
  * entitled token + good input -> 200, brief HTML rendered, credit consumed
  * entitled token + uncited claim -> 422 (fail-closed; no brief)
  * missing token / topic       -> 402 / 400

Run:  python3 -m unittest tests.test_generate -v     (from the product root)
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Load api/generate.py by path (the `api` dir is not a package).
_spec = importlib.util.spec_from_file_location(
    "hrf_generate", os.path.join(_ROOT, "api", "generate.py")
)
generate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate)


SOURCES = [
    {
        "id": "s1",
        "title": "Illustrative hydration reference (example)",
        "url": "https://example.org/hydration-basics",
        "retrieved_at": "2026-07-16T00:00:00Z",
        "text": "Drinking water supports normal body temperature regulation during exercise.",
    }
]
GOOD_CLAIMS = [
    {
        "text": "Water helps regulate body temperature during exercise.",
        "citations": [
            {"source_id": "s1", "quote": "supports normal body temperature regulation during exercise"}
        ],
    }
]
UNCITED_CLAIMS = GOOD_CLAIMS + [{"text": "An uncited claim with no source.", "citations": []}]


class GenerateRouteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        # Seed the store the way the webhook would: one-off brief token = 1 credit.
        json.dump({"tok_paid": {"tier": "brief", "remaining": 1}}, self.tmp)
        self.tmp.close()
        os.environ["HRF_ENTITLEMENTS_PATH"] = self.tmp.name

    def tearDown(self):
        os.unlink(self.tmp.name)
        os.environ.pop("HRF_ENTITLEMENTS_PATH", None)

    def _body(self, **over):
        b = {"token": "tok_paid", "topic": "Hydration", "sources": SOURCES, "claims": GOOD_CLAIMS}
        b.update(over)
        return b

    def test_missing_token_is_402(self):
        status, payload = generate.build_response({"topic": "x", "sources": SOURCES, "claims": GOOD_CLAIMS})
        self.assertEqual(status, 402)
        self.assertEqual(payload["error"], "not_entitled")

    def test_missing_topic_is_400(self):
        status, payload = generate.build_response(self._body(topic=""))
        self.assertEqual(status, 400)

    def test_unentitled_token_is_402(self):
        status, payload = generate.build_response(self._body(token="tok_never_bought"))
        self.assertEqual(status, 402)
        self.assertEqual(payload["error"], "not_entitled")

    def test_entitled_renders_and_consumes(self):
        status, payload = generate.build_response(self._body())
        self.assertEqual(status, 200, payload)
        self.assertIn("Clarity Brief", payload["html"])
        self.assertGreaterEqual(payload["coverage_pct"], 100.0)
        # Credit consumed -> a second call with the same one-off token is denied.
        status2, _ = generate.build_response(self._body())
        self.assertEqual(status2, 402)

    def test_uncited_claim_fails_closed_422(self):
        status, payload = generate.build_response(self._body(claims=UNCITED_CLAIMS))
        self.assertEqual(status, 422)
        self.assertEqual(payload["error"], "lint_failed")
        self.assertIn("summary", payload)


if __name__ == "__main__":
    unittest.main()
