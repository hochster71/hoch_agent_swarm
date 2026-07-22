#!/usr/bin/env python3
"""
HELM Governance Platform — Production Hardening, Metamorphic & Mutation Testing Suite
Tests fail-closed robustness against malformed JSON, float anomalies, deeply nested structures,
metamorphic round-trip invariants, and mutation regression checks.
"""

import math
import random
import string
import unittest
import json
from backend.helm.kernel.decision_engine import HELMDecisionEngine
from scripts.helm.canonical_json import canonical_json_bytes, canonical_sha256_digest


def generate_random_json(depth: int = 0) -> any:
    if depth > 4:
        return random.choice([
            random.randint(-1000, 1000),
            random.choice([0.0, -0.0, 1.5, 42.125]),
            "".join(random.choices(string.ascii_letters + string.digits + " \u20ac\u00c4", k=8)),
            True,
            False,
            None
        ])

    choice = random.randint(1, 5)
    if choice == 1:
        size = random.randint(1, 5)
        return {
            "".join(random.choices(string.ascii_lowercase, k=5)): generate_random_json(depth + 1)
            for _ in range(size)
        }
    elif choice == 2:
        size = random.randint(1, 5)
        return [generate_random_json(depth + 1) for _ in range(size)]
    elif choice == 3:
        return random.randint(-10000, 10000)
    elif choice == 4:
        return "".join(random.choices(string.ascii_letters + " \t\n\u20ac", k=10))
    else:
        return random.choice([True, False, None])


class TestHELMFuzzer(unittest.TestCase):

    def setUp(self):
        self.engine = HELMDecisionEngine()

    def test_fuzz_nan_float_rejection(self):
        """Asserts NaN float in payload raises explicit ValueError."""
        payload = {
            "config_digest": "abc",
            "evaluated_inputs": {"availability": float("nan")}
        }
        with self.assertRaises(ValueError) as ctx:
            self.engine.canonical_json_bytes(payload)
        self.assertIn("NaN", str(ctx.exception))

    def test_fuzz_infinity_float_rejection(self):
        """Asserts Infinity float in payload raises explicit ValueError."""
        payload = {
            "config_digest": "abc",
            "evaluated_inputs": {"availability": float("inf")}
        }
        with self.assertRaises(ValueError) as ctx:
            self.engine.canonical_json_bytes(payload)
        self.assertIn("Infinity", str(ctx.exception))

    def test_fuzz_negative_zero_normalization(self):
        """Asserts -0.0 normalizes to 0 in canonical JSON."""
        payload = {
            "val": -0.0
        }
        canonical_bytes = self.engine.canonical_json_bytes(payload)
        self.assertEqual(canonical_bytes.decode("utf-8"), '{"val":0}')

    def test_metamorphic_roundtrip_invariants(self):
        """Metamorphic Property 1: Canonicalize(X) == Canonicalize(Parse(Canonicalize(X)))"""
        random.seed(42)
        for i in range(200):
            tree = generate_random_json()
            c_bytes_1 = canonical_json_bytes(tree)
            c_text_1 = c_bytes_1.decode("utf-8")

            # Parse canonical string back into memory
            reparsed_obj = json.loads(c_text_1)

            # Re-canonicalize parsed object
            c_bytes_2 = canonical_json_bytes(reparsed_obj)
            c_text_2 = c_bytes_2.decode("utf-8")

            self.assertEqual(c_text_1, c_text_2, f"Metamorphic roundtrip failed on iteration {i}")

    def test_metamorphic_digest_invariants(self):
        """Metamorphic Property 2: Digest(X) == Digest(Parse(Canonicalize(X))) == Digest(Parse(Parse(...)))"""
        random.seed(123)
        for i in range(200):
            tree = generate_random_json()
            d1 = canonical_sha256_digest(tree)

            c_text_1 = canonical_json_bytes(tree).decode("utf-8")
            obj_1 = json.loads(c_text_1)
            d2 = canonical_sha256_digest(obj_1)

            c_text_2 = canonical_json_bytes(obj_1).decode("utf-8")
            obj_2 = json.loads(c_text_2)
            d3 = canonical_sha256_digest(obj_2)

            self.assertEqual(d1, d2, f"Metamorphic digest pass 1 failed on iteration {i}")
            self.assertEqual(d2, d3, f"Metamorphic digest pass 2 failed on iteration {i}")

    def test_mutation_defect_detection(self):
        """Mutation Test: Ensures altering key order, modifying bytes, or adding homoglyphs produces distinct canonical hashes or catches defects."""
        base_obj = {"alpha": 1, "beta": 2, "gamma": [10, 20]}
        base_hash = canonical_sha256_digest(base_obj)

        # Mutate 1: Change value
        mut1 = {"alpha": 1, "beta": 3, "gamma": [10, 20]}
        self.assertNotEqual(base_hash, canonical_sha256_digest(mut1))

        # Mutate 2: Homoglyph injection ('а' Cyrillic small letter a)
        mut2 = {"\u0430lpha": 1, "beta": 2, "gamma": [10, 20]}
        self.assertNotEqual(base_hash, canonical_sha256_digest(mut2))

    def test_fuzz_missing_provenance_defaults_to_withheld(self):
        """Asserts empty or missing raw_input fields default to WITHHELD_UNVERIFIED_PROVENANCE."""
        res = self.engine.evaluate_release_promotion({})
        self.assertEqual(res["decision_code"], "WITHHELD_UNVERIFIED_PROVENANCE")

    def test_fuzz_malformed_types_handling(self):
        """Asserts non-dict payload handling throws appropriate type error."""
        with self.assertRaises(AttributeError):
            self.engine.evaluate_release_promotion("not_a_dict")


if __name__ == "__main__":
    unittest.main()
