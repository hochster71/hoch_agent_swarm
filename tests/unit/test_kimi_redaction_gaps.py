"""Adversarial coverage tests for the Kimi safe-handoff redactor.

Context: `scripts/kimi/make_safe_handoff.py` was built and smoke-tested by a separate
agent session on 2026-07-20. The smoke test passed. This file is the independent
verification, and it FAILS — the redactor ships five live-format credential classes.

These tests are written to FAIL until the gaps are closed. That is deliberate: a red
test is the honest representation of a known hole. Do not skip them to get green.

WHY THIS MATTERS MORE THAN A NORMAL COVERAGE GAP
------------------------------------------------
This redactor is the ONLY barrier between the monorepo and an external agent's
workspace (`~/Documents/kimi/workspace/_inbox_from_helm/`). A miss is not a bug that
degrades output — it is a credential leaving the trust boundary. And the packager
currently reports `DRY-RUN: OK` on a file containing all five, because:

    RESIDUAL_FORBIDDEN ⊂ SECRET_SPECS families

The post-redaction residual scan reuses a strict subset of the redactor's own pattern
families. It therefore cannot detect a class the redactor does not know. The system has
two checks but only one hypothesis about what a secret looks like, so "fail-closed" is
only as wide as that hypothesis.

All fixtures below are syntactically valid but FAKE. No real credential appears here.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGER = ROOT / "scripts" / "kimi" / "make_safe_handoff.py"

pytestmark = pytest.mark.skipif(
    not PACKAGER.exists(), reason="kimi packager not present in this checkout"
)

# (id, fixture line, why it matters) — every value is fake.
LEAKY = [
    ("openai_project_key",
     "sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz1234567890abcd",
     "openai_key pattern requires 20+ alnum immediately after 'sk-'; the 'proj-' "
     "segment contains a hyphen, so the match fails and the key ships"),
    ("google_api_key",
     "AIzaSyD-1234567890abcdefghijklmnopqrstu",
     "no AIza pattern exists; Google/Firebase keys are unhandled"),
    ("sendgrid_key",
     "SG.AbCdEfGhIjKlMnOpQr.1234567890abcdefghijklmnopqrstuvwxyz12",
     "no SG. pattern exists"),
    ("npm_token",
     "npm_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890",
     "no npm_ pattern exists"),
    ("digitalocean_token",
     "dop_v1_abcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678",
     "no dop_v1_ pattern exists"),
]


def _pack(tmp_path: Path, content: str) -> str:
    """Run the packager in dry-run against a file and return combined output."""
    probe = ROOT / "_pytest_redaction_probe.txt"
    probe.write_text(content, encoding="utf-8")
    try:
        r = subprocess.run(
            [sys.executable, str(PACKAGER), probe.name, "--dry-run"],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        return (r.stdout or "") + (r.stderr or "")
    finally:
        probe.unlink(missing_ok=True)


@pytest.mark.parametrize("name,fixture,why", LEAKY, ids=[x[0] for x in LEAKY])
def test_credential_class_is_redacted(tmp_path, name, fixture, why):
    """Each known credential format must be redacted or refuse the pack."""
    out = _pack(tmp_path, f"CONFIG = '{fixture}'\n")
    redacted = "REDACTED" in out
    refused = "DRY-RUN: OK" not in out
    assert redacted or refused, (
        f"{name} passed through un-redacted and the pack was approved.\n"
        f"reason: {why}"
    )


def test_residual_scan_is_independent_of_redactor():
    """The post-redaction check must not reuse only the redactor's own hypotheses.

    A second check drawn from the same pattern families provides no additional
    assurance: anything the redactor cannot see, the residual scan cannot see either.
    """
    src = PACKAGER.read_text(encoding="utf-8")
    residual_block = src.split("RESIDUAL_FORBIDDEN")[1].split("]")[0]
    # A genuinely independent check would look for high-entropy strings, or for any
    # token matching a broad credential shape, rather than the same five families.
    has_entropy_check = any(
        k in src for k in ("entropy", "shannon", "base64_blob", "HIGH_ENTROPY")
    )
    families = ("sk_live_", "sk-ant-", "ghp_", "PRIVATE KEY", "AKIA")
    only_known_families = all(f in residual_block for f in families)
    assert has_entropy_check, (
        "RESIDUAL_FORBIDDEN reuses a subset of SECRET_SPECS families "
        f"(only_known_families={only_known_families}) and there is no entropy-based "
        "backstop. Add a generic high-entropy / unknown-token check so the second "
        "gate can catch classes the first gate does not model."
    )


# --- false positives: the gate's durability risk ------------------------------
#
# Verified 2026-07-20: the entropy backstop closed every credential class tested,
# including six never named in this file (Shopify, Grafana, Square, Facebook,
# HuggingFace, Stripe restricted). The gate is real.
#
# The remaining risk is not a miss — it is noise. A security gate that blocks routine
# packs gets bypassed, and a bypassed gate protects nothing. Each fixture below is a
# high-entropy string that is unambiguously NOT a secret and is common in any real
# codebase. All of them currently fail the pack.
#
# Fix shape: an allowlist of well-known benign high-entropy forms, applied BEFORE the
# entropy check, so the gate keeps its teeth on unknown credential shapes.

BENIGN_HIGH_ENTROPY = [
    ("git_sha_40", 'COMMIT = "78fa433da1b2c3d4e5f6789012345678901234ab"',
     "git object IDs appear in lockfiles, submodules, changelogs, pinned deps"),
    ("sha256_hex", 'H = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"',
     "content hashes appear in every lockfile and integrity manifest"),
    ("sri_integrity", 'T = "sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC"',
     "Subresource Integrity attributes appear in every CDN script tag"),
    ("base64_png_data_uri",
     'CSS = "background:url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ)"',
     "inline images are routine in CSS and email templates"),
]


@pytest.mark.parametrize("name,fixture,why", BENIGN_HIGH_ENTROPY,
                         ids=[x[0] for x in BENIGN_HIGH_ENTROPY])
def test_benign_high_entropy_does_not_block_the_pack(tmp_path, name, fixture, why):
    """Well-known non-secret high-entropy forms must not fail an otherwise clean pack."""
    out = _pack(tmp_path, fixture + "\n")
    assert "DRY-RUN: OK" in out, (
        f"{name} blocked a clean pack as HIGH_ENTROPY.\n"
        f"why it is benign: {why}\n"
        "A gate this noisy will be bypassed in practice, which forfeits the real "
        "protection it provides against unknown credential shapes."
    )


# --- allowlist shape-collision: the hole the FP fix opened ---------------------
#
# Verified 2026-07-20, after commit 006c0232. The benign allowlist works as specified
# and, exactly because it is SHAPE-based, it now trusts real credentials that share a
# shape with a hash. All four fixtures below pack clean (DRY-RUN: OK).
#
# This is the cost of the false-positive fix, not a mistake in implementing it. A
# 64-hex webhook secret and a SHA-256 digest are indistinguishable by shape. They are
# trivially distinguishable by CONTEXT: the variable is named SECRET.
#
# Required fix: the benign allowlist must not apply when the assignment target or
# nearby key matches a credential-ish name (secret|token|key|password|credential|auth).
# Shape may say "could be a hash"; context saying "is a secret" must win.
#
# Note the existing `api_key_assign` pattern does not cover these either — it matches
# api_key / access_token / client_secret / private_key, but not WEBHOOK_SECRET or
# COINBASE_API_SECRET. The name vocabulary needs widening at the same time.

SHAPE_COLLISION = [
    ("hex64_named_secret",
     'WEBHOOK_SECRET = "a3f5c8e1b9d24760af31c5e8d92b4a6f7c0e83d15b92746af38c1e5d0b7a942e"',
     "64-hex is allowlisted as SHA-256; many webhook signing secrets are exactly this"),
    ("hex32_named_secret",
     'COINBASE_API_SECRET = "9f2c4a7e1d8b3506cf9e2a4d7b1c8e35"',
     "32-hex below entropy threshold and name not in api_key_assign vocabulary"),
    ("hex40_named_token",
     'LEGACY_TOKEN = "78fa433da1b2c3d4e5f6789012345678901234ab"',
     "40-hex is allowlisted as a git SHA regardless of what the variable is called"),
    ("sri_prefixed_session_key",
     'SESSION_KEY = "sha256-Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MGFiY2RlZmdoaWprbG1ub3A="',
     "an attacker-or-accident 'sha256-' prefix buys blanket SRI trust"),
]


@pytest.mark.parametrize("name,fixture,why", SHAPE_COLLISION,
                         ids=[x[0] for x in SHAPE_COLLISION])
def test_credential_named_variable_defeats_benign_allowlist(tmp_path, name, fixture, why):
    """A credential-ish variable name must override the benign-shape allowlist."""
    out = _pack(tmp_path, fixture + "\n")
    redacted = "REDACTED" in out
    refused = "DRY-RUN: OK" not in out
    assert redacted or refused, (
        f"{name} packed clean because its SHAPE matched the benign allowlist.\n"
        f"why that is wrong: {why}\n"
        "Gate the allowlist on context: do not apply it when the assignment target "
        "matches (?i)(secret|token|key|password|credential|auth)."
    )


def test_uuid_is_already_tolerated():
    """Regression guard: UUIDs were correctly NOT flagged. Keep it that way."""
    out = _pack(Path("."), 'ID = "550e8400-e29b-41d4-a716-446655440000"\n')
    assert "DRY-RUN: OK" in out


def test_concatenated_secret_is_known_limitation():
    """Documented, not fixed: a split literal defeats regex redaction.

    Kept as a live test so the limitation stays visible rather than becoming folklore.
    Static regex cannot see through string concatenation; the mitigation is the
    deny-list (never pack files that build credentials), not a better pattern.
    """
    out = _pack(Path("."), 'S = "".join(["sk_l","ive_","AbCdEfGhIjKlMnOpQrStUv"])\n')
    assert "DRY-RUN: OK" in out, (
        "behaviour changed — concatenated-secret handling now differs; "
        "re-evaluate whether the deny-list mitigation is still the right answer"
    )
