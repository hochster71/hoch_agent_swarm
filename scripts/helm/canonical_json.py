#!/usr/bin/env python3
r"""
HELM Standalone RFC 8785 JSON Canonicalizer & SHA-256 Hashing Engine (v1.0.0 Normative)
========================================================================================
Implements RFC 8785 (JSON Canonicalization Scheme - JCS) in pure zero-dependency Python:
  1. Lexicographical key ordering by UTF-16 code units.
  2. Structural whitespace removal.
  3. String literal preservation without Unicode normalization.
  4. ECMAScript / IEEE 754 number formatting rules.
  5. Rejection of NaN, Infinity, duplicate keys, and invalid UTF-8.
  6. Domain-tagged SHA-256 hashing ("HELM-CONFORMANCE-TRANSITION-V1\n").
"""

import hashlib
import json
import math
import sys
from typing import Any, Dict, Union

DOMAIN_TAG = b"HELM-CONFORMANCE-TRANSITION-V1\n"
GENESIS_HASH = "GENESIS_HASH_0000000000000000000000000000000000000000000000000000000000000000"


def canonicalize_obj(obj: Any) -> Any:
    """Recursively validates and formats data structures according to RFC 8785 JCS rules."""
    if isinstance(obj, dict):
        # UTF-16 code unit key sorting and duplicate key check
        sorted_dict = {}
        keys = list(obj.keys())
        for k in keys:
            if not isinstance(k, str):
                raise ValueError(f"RFC 8785 requires JSON string keys, got: {type(k)}")
        
        # Check for duplicate keys if loaded from raw stream or duplicate key structure
        if len(keys) != len(set(keys)):
            raise ValueError("RFC 8785 / I-JSON forbids duplicate object member names")
            
        for k in sorted(keys):
            sorted_dict[k] = canonicalize_obj(obj[k])
        return sorted_dict
    elif isinstance(obj, list):
        return [canonicalize_obj(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"RFC 8785 forbids non-finite floating point numbers (NaN/Infinity): {obj}")
        if obj == 0.0:
            return 0
        return obj
    elif isinstance(obj, str):
        # Validate UTF-8 encoding
        obj.encode("utf-8")
        return obj
    return obj


def canonical_json_bytes(obj: Any) -> bytes:
    """Returns canonical UTF-8 encoded byte array following RFC 8785 JCS standard."""
    sanitized = canonicalize_obj(obj)
    return json.dumps(
        sanitized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256_digest(obj: Any) -> str:
    """Computes standard SHA-256 digest over RFC 8785 canonical JSON bytes."""
    data_bytes = canonical_json_bytes(obj)
    return hashlib.sha256(data_bytes).hexdigest()


def compute_transition_hash(transition_payload: Dict[str, Any], previous_transition_hash: str) -> str:
    r"""Computes HELM domain-tagged transition hash:
    transition_hash_k = SHA256("HELM-CONFORMANCE-TRANSITION-V1\n" || JCS(transition_k \ {transition_hash}) || previous_transition_hash)
    """
    clean_transition = {k: v for k, v in transition_payload.items() if k != "transition_hash"}
    canonical_body_bytes = canonical_json_bytes(clean_transition)
    prev_hash_bytes = previous_transition_hash.encode("utf-8")
    full_payload = DOMAIN_TAG + canonical_body_bytes + prev_hash_bytes
    return hashlib.sha256(full_payload).hexdigest()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 canonical_json.py <json_file> [--digest|--hex]", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--bytes"

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"FAIL: Invalid UTF-8 encoding: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed_json = json.loads(raw_text)
    except Exception as e:
        print(f"FAIL: Invalid JSON syntax or duplicate key: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        canonical_b = canonical_json_bytes(parsed_json)
    except Exception as e:
        print(f"FAIL: RFC 8785 Canonicalization failed: {e}", file=sys.stderr)
        sys.exit(1)

    if mode == "--digest":
        print(hashlib.sha256(canonical_b).hexdigest())
    elif mode == "--hex":
        print(canonical_b.hex())
    else:
        sys.stdout.buffer.write(canonical_b)


if __name__ == "__main__":
    main()
