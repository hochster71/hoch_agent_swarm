"""Live App Store Connect reader for the Epic Fury champion gates (TESTFLIGHT,
APP_STORE_CONNECT).

Doctrine: a local JSON asserting success is NOT evidence. This module reads the REAL
state from Apple's App Store Connect API and reports it. It is FAIL-CLOSED: any missing
credential, network error, auth failure, or unexpected response yields state UNKNOWN
with a reason — never a fabricated PASS.

Credentials are read from the environment at runtime and are NEVER logged or returned:
  APP_STORE_CONNECT_KEY_ID    - the API key id (kid)
  APP_STORE_CONNECT_ISSUER_ID - the issuer id (iss)
  ASC_API_KEY                 - the ES256 private key: either the PEM (.p8) CONTENTS
                                or a path to the .p8 file
Optional:
  HELM_ASC_BUNDLE_ID          - defaults to com.epicfury.dashboard
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

ASC_BASE = "https://api.appstoreconnect.apple.com/v1"
DEFAULT_BUNDLE_ID = "com.epicfury.dashboard"
UNKNOWN = "UNKNOWN"


class ASCUnavailable(Exception):
    """Raised internally when a live read cannot be completed. Callers convert this
    to a fail-closed UNKNOWN result — never to a PASS."""


def _load_private_key() -> str:
    raw = (os.environ.get("ASC_API_KEY") or "").strip()
    if not raw:
        raise ASCUnavailable("ASC_API_KEY not set")
    if "BEGIN PRIVATE KEY" in raw:
        return raw
    p = Path(os.path.expanduser(raw))
    if p.exists():
        return p.read_text()
    raise ASCUnavailable("ASC_API_KEY is neither PEM contents nor an existing .p8 path")


def _bearer_token() -> str:
    kid = (os.environ.get("APP_STORE_CONNECT_KEY_ID") or "").strip()
    iss = (os.environ.get("APP_STORE_CONNECT_ISSUER_ID") or "").strip()
    if not kid or not iss:
        raise ASCUnavailable("APP_STORE_CONNECT_KEY_ID / ISSUER_ID not set")
    try:
        import jwt  # PyJWT
    except Exception as e:  # pragma: no cover
        raise ASCUnavailable(f"PyJWT unavailable: {e}")
    now = int(time.time())
    payload = {"iss": iss, "iat": now, "exp": now + 15 * 60, "aud": "appstoreconnect-v1"}
    try:
        return jwt.encode(payload, _load_private_key(), algorithm="ES256",
                          headers={"kid": kid, "typ": "JWT"})
    except Exception as e:
        raise ASCUnavailable(f"JWT signing failed: {e}")


def _get(path: str, params: Optional[dict] = None) -> dict:
    import requests
    token = _bearer_token()  # credential/JWT errors surface as themselves, not "network error"
    try:
        r = requests.get(f"{ASC_BASE}{path}", params=params or {},
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
    except Exception as e:
        raise ASCUnavailable(f"network error: {str(e)[:120]}")
    if r.status_code == 401:
        raise ASCUnavailable("401 from App Store Connect (bad/expired credentials)")
    if r.status_code >= 400:
        raise ASCUnavailable(f"ASC API {r.status_code}: {r.text[:120]}")
    try:
        return r.json()
    except Exception as e:
        raise ASCUnavailable(f"non-JSON response: {e}")


def _app_id(bundle_id: str) -> str:
    data = _get("/apps", {"filter[bundleId]": bundle_id, "limit": 1}).get("data", [])
    if not data:
        raise ASCUnavailable(f"no app in App Store Connect for bundleId {bundle_id}")
    return data[0]["id"]


def read_distribution_state(bundle_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the REAL TestFlight + App Store review state, fail-closed to UNKNOWN.

    Shape:
      {"testflight": {"state": PASS|FAIL|UNKNOWN, "detail": ..., "evidence": "asc:builds"},
       "app_store":  {"state": PASS|FAIL|UNKNOWN, "detail": ..., "evidence": "asc:appStoreVersions"},
       "read_at": iso}
    Never raises; on any problem both sub-states are UNKNOWN with the reason.
    """
    import datetime
    bundle_id = bundle_id or os.environ.get("HELM_ASC_BUNDLE_ID") or DEFAULT_BUNDLE_ID
    out = {"read_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "bundle_id": bundle_id}
    try:
        app_id = _app_id(bundle_id)
    except ASCUnavailable as e:
        reason = str(e)
        out["testflight"] = {"state": UNKNOWN, "detail": reason, "evidence": "asc:none"}
        out["app_store"] = {"state": UNKNOWN, "detail": reason, "evidence": "asc:none"}
        return out

    # ---- TestFlight: newest builds + processing state -----------------------
    try:
        builds = _get("/builds", {"filter[app]": app_id, "sort": "-uploadedDate",
                                  "limit": 5}).get("data", [])
        if not builds:
            out["testflight"] = {"state": UNKNOWN, "detail": "no builds uploaded to App Store Connect yet",
                                 "evidence": "asc:builds"}
        else:
            b = builds[0]["attributes"]
            proc = b.get("processingState")
            ver = b.get("version")
            if proc == "VALID":
                out["testflight"] = {"state": "PASS",
                                     "detail": f"build {ver} processed (VALID) in TestFlight",
                                     "evidence": "asc:builds"}
            else:
                out["testflight"] = {"state": UNKNOWN,
                                     "detail": f"newest build {ver} processingState={proc} (not yet VALID)",
                                     "evidence": "asc:builds"}
    except ASCUnavailable as e:
        out["testflight"] = {"state": UNKNOWN, "detail": str(e), "evidence": "asc:builds"}

    # ---- App Store: newest version review/release state ---------------------
    try:
        vers = _get(f"/apps/{app_id}/appStoreVersions", {"limit": 3}).get("data", [])
        if not vers:
            out["app_store"] = {"state": UNKNOWN, "detail": "no App Store version created yet",
                                "evidence": "asc:appStoreVersions"}
        else:
            a = vers[0]["attributes"]
            st = a.get("appStoreState") or a.get("state")
            vs = a.get("versionString")
            # 'shipped to production' == live/approved states; in-review is progress but not shipped.
            # Apple renamed "Ready for Sale" -> "Ready for Distribution"; accept both.
            LIVE = {"READY_FOR_SALE", "READY_FOR_DISTRIBUTION",
                    "PENDING_DEVELOPER_RELEASE", "PROCESSING_FOR_APP_STORE"}
            REJECTED = {"REJECTED", "DEVELOPER_REJECTED", "METADATA_REJECTED", "INVALID_BINARY"}
            if st in LIVE:
                out["app_store"] = {"state": "PASS", "detail": f"version {vs} appStoreState={st}",
                                    "evidence": "asc:appStoreVersions"}
            elif st in REJECTED:
                out["app_store"] = {"state": "FAIL", "detail": f"version {vs} appStoreState={st}",
                                    "evidence": "asc:appStoreVersions"}
            else:
                out["app_store"] = {"state": UNKNOWN,
                                    "detail": f"version {vs} appStoreState={st} (in progress, not yet shipped)",
                                    "evidence": "asc:appStoreVersions"}
    except ASCUnavailable as e:
        out["app_store"] = {"state": UNKNOWN, "detail": str(e), "evidence": "asc:appStoreVersions"}

    return out


if __name__ == "__main__":
    import json
    print(json.dumps(read_distribution_state(), indent=2))
