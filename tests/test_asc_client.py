"""App Store Connect live-read client — fail-closed + auth + parsing.

Cannot make a real authenticated Apple call in CI (needs the founder's live creds), so
this proves: (1) no creds -> UNKNOWN, never crashes and never PASS; (2) the ES256 JWT is
built correctly; (3) live ASC responses map to the right PASS/FAIL/UNKNOWN state.
"""
import importlib

import pytest

asc = importlib.import_module("scripts.goal.asc_client")

ASC_ENV = ["ASC_API_KEY", "APP_STORE_CONNECT_KEY_ID", "APP_STORE_CONNECT_ISSUER_ID"]


def _clear(monkeypatch):
    for v in ASC_ENV:
        monkeypatch.delenv(v, raising=False)


def test_fail_closed_without_credentials(monkeypatch):
    _clear(monkeypatch)
    r = asc.read_distribution_state("com.example.app")
    assert r["testflight"]["state"] == asc.UNKNOWN
    assert r["app_store"]["state"] == asc.UNKNOWN
    # never a PASS, never raised
    assert "PASS" not in (r["testflight"]["state"], r["app_store"]["state"])


def test_es256_jwt_is_valid(monkeypatch):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setenv("ASC_API_KEY", pem)
    monkeypatch.setenv("APP_STORE_CONNECT_KEY_ID", "KID123")
    monkeypatch.setenv("APP_STORE_CONNECT_ISSUER_ID", "ISS-abc")

    tok = asc._bearer_token()
    decoded = jwt.decode(tok, pub, algorithms=["ES256"], audience="appstoreconnect-v1")
    assert decoded["iss"] == "ISS-abc"
    assert jwt.get_unverified_header(tok)["kid"] == "KID123"


def test_state_mapping(monkeypatch):
    monkeypatch.setattr(asc, "_app_id", lambda bundle_id: "app-1")

    def fake_get(path, params=None):
        if path == "/builds":
            return {"data": [{"attributes": {"processingState": "VALID", "version": "42"}}]}
        if path.endswith("/appStoreVersions"):
            return {"data": [{"attributes": {"appStoreState": "READY_FOR_SALE", "versionString": "1.0"}}]}
        return {"data": []}

    monkeypatch.setattr(asc, "_get", fake_get)
    r = asc.read_distribution_state("com.epicfury.dashboard")
    assert r["testflight"]["state"] == "PASS"
    assert r["app_store"]["state"] == "PASS"

    # rejected version -> FAIL; unprocessed build -> UNKNOWN
    def fake_get2(path, params=None):
        if path == "/builds":
            return {"data": [{"attributes": {"processingState": "PROCESSING", "version": "43"}}]}
        if path.endswith("/appStoreVersions"):
            return {"data": [{"attributes": {"appStoreState": "REJECTED", "versionString": "1.0"}}]}
        return {"data": []}

    monkeypatch.setattr(asc, "_get", fake_get2)
    r2 = asc.read_distribution_state("com.epicfury.dashboard")
    assert r2["testflight"]["state"] == asc.UNKNOWN     # not yet VALID
    assert r2["app_store"]["state"] == "FAIL"           # rejected


def test_no_build_is_unknown_not_fail(monkeypatch):
    monkeypatch.setattr(asc, "_app_id", lambda bundle_id: "app-1")
    monkeypatch.setattr(asc, "_get", lambda path, params=None: {"data": []})
    r = asc.read_distribution_state("com.epicfury.dashboard")
    assert r["testflight"]["state"] == asc.UNKNOWN
    assert r["app_store"]["state"] == asc.UNKNOWN
