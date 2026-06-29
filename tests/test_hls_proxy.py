"""
tests/test_hls_proxy.py
=======================
Unit + integration tests for the HLS server-side proxy.

Coverage matrix
---------------
1. host_allowlist          – allowed hosts pass, unknown hosts blocked.
2. m3u8_playlist_rewrite   – all segment URLs rewritten through /api/hls/proxy.
3. blocked_host            – GET /api/hls/proxy?url=<evil> → HTTP 403.
4. upstream_403            – upstream returns 403 → proxy returns HTTP 502
                             with HLS_PROXY_UPSTREAM_403 in detail.
5. upstream_404            – upstream returns 404 → proxy returns HTTP 404
                             with HLS_PROXY_UPSTREAM_404 in detail.
6. frontend_proxy_url      – buildHlsProxyUrl logic validated in Python.
7. info_endpoint           – GET /api/hls/proxy/info returns allowlist JSON.
8. invalid_url             – missing scheme → HTTP 400.
9. absolute_url_in_m3u8   – absolute URLs inside playlist rewritten.
10. key_uri_rewrite        – EXT-X-KEY URI attribute is rewritten.
11. relative_segments      – relative segment paths resolved and rewritten.
"""

import pytest
import urllib.error
from unittest.mock import patch, MagicMock
from urllib.parse import quote, urlencode

from fastapi.testclient import TestClient
from backend.main import app
from backend.hls_proxy import (
    HLS_ALLOWED_HOSTS,
    is_host_allowed,
    build_proxy_url,
    _content_type_for,
    _is_playlist,
    _rewrite_playlist,
)

client = TestClient(app)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_M3U8 = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="https://g1o.empek.xyz/key/abc123.key",IV=0x0
#EXTINF:9.009,
https://g1o.empek.xyz/hls/seg000.ts
#EXTINF:9.009,
seg001.ts
#EXTINF:9.009,
/hls/seg002.ts
#EXT-X-ENDLIST
"""

REMOTE_PLAYLIST_URL = "https://g1o.empek.xyz/hls/live.m3u8"
ALLOWED_HOST = "g1o.empek.xyz"
BLOCKED_HOST = "evil.example.com"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Host allowlist
# ─────────────────────────────────────────────────────────────────────────────

def test_allowed_hosts_contain_drogon():
    """Core Drogon TV domains must be in the allowlist."""
    assert "drogon.tv" in HLS_ALLOWED_HOSTS
    assert "g1o.empek.xyz" in HLS_ALLOWED_HOSTS


def test_is_host_allowed_passes_for_known_host():
    assert is_host_allowed("https://g1o.empek.xyz/hls/live.m3u8") is True


def test_is_host_allowed_passes_for_drogon():
    assert is_host_allowed("https://drogon.tv/live/index.m3u8") is True


def test_is_host_allowed_blocks_unknown_host():
    assert is_host_allowed(f"https://{BLOCKED_HOST}/stream.m3u8") is False


def test_is_host_allowed_blocks_empty():
    assert is_host_allowed("") is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. m3u8 playlist rewrite (unit)
# ─────────────────────────────────────────────────────────────────────────────

def test_playlist_rewrite_absolute_segment():
    rewritten = _rewrite_playlist(SAMPLE_M3U8, REMOTE_PLAYLIST_URL)
    assert "/api/hls/proxy?url=" in rewritten
    assert "https://g1o.empek.xyz/hls/seg000.ts" not in rewritten


def test_playlist_rewrite_relative_segment_resolved():
    rewritten = _rewrite_playlist(SAMPLE_M3U8, REMOTE_PLAYLIST_URL)
    # seg001.ts should be resolved to https://g1o.empek.xyz/hls/seg001.ts
    # and that URL should appear encoded inside a proxy URL
    encoded_seg001 = quote("https://g1o.empek.xyz/hls/seg001.ts", safe="")
    assert encoded_seg001 in rewritten


def test_playlist_rewrite_key_uri():
    rewritten = _rewrite_playlist(SAMPLE_M3U8, REMOTE_PLAYLIST_URL)
    # The EXT-X-KEY URI must point through the proxy, not directly to the CDN
    assert 'URI="/api/hls/proxy?url=' in rewritten or 'URI=\'/api/hls/proxy?url=' in rewritten
    # The raw CDN key URL must not appear unencoded as a direct URI value
    assert 'URI="https://g1o.empek.xyz' not in rewritten


def test_playlist_rewrite_preserves_extm3u_header():
    rewritten = _rewrite_playlist(SAMPLE_M3U8, REMOTE_PLAYLIST_URL)
    assert rewritten.startswith("#EXTM3U")


def test_playlist_rewrite_preserves_extinf_tags():
    rewritten = _rewrite_playlist(SAMPLE_M3U8, REMOTE_PLAYLIST_URL)
    assert "#EXTINF:9.009," in rewritten


def test_playlist_rewrite_blocks_unknown_host_segments():
    evil_m3u8 = "#EXTM3U\n#EXTINF:9,\nhttps://evil.example.com/seg.ts\n"
    rewritten = _rewrite_playlist(evil_m3u8, REMOTE_PLAYLIST_URL)
    # Should be replaced with a comment, not a live URL
    assert "evil.example.com" not in rewritten or "HLS_PROXY_BLOCKED_HOST" in rewritten
    assert "/api/hls/proxy?url=https%3A%2F%2Fevil.example.com" not in rewritten


# ─────────────────────────────────────────────────────────────────────────────
# 3. Blocked host via FastAPI endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_proxy_endpoint_blocks_unknown_host():
    url = f"https://{BLOCKED_HOST}/live.m3u8"
    resp = client.get(f"/api/hls/proxy?url={quote(url, safe='')}")
    assert resp.status_code == 403
    assert "HLS_PROXY_BLOCKED" in resp.json()["detail"]


def test_proxy_endpoint_blocks_when_url_missing():
    resp = client.get("/api/hls/proxy?url=not_a_real_url")
    assert resp.status_code in (400, 403)


def test_proxy_endpoint_rejects_missing_scheme():
    resp = client.get(f"/api/hls/proxy?url={quote('g1o.empek.xyz/hls/live.m3u8', safe='')}")
    assert resp.status_code == 400
    assert "HLS_PROXY_ERROR" in resp.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Upstream HTTP 403 handling
# ─────────────────────────────────────────────────────────────────────────────

def test_proxy_returns_502_on_upstream_403():
    """When the CDN returns 403, the proxy must return 502 with a clear message."""
    url = f"https://{ALLOWED_HOST}/blocked.m3u8"

    mock_403 = urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

    with patch("backend.hls_proxy.urllib.request.urlopen", side_effect=mock_403):
        resp = client.get(f"/api/hls/proxy?url={quote(url, safe='')}")

    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert "403" in detail or "HLS_PROXY_UPSTREAM_403" in detail


# ─────────────────────────────────────────────────────────────────────────────
# 5. Upstream HTTP 404 handling
# ─────────────────────────────────────────────────────────────────────────────

def test_proxy_returns_404_on_upstream_404():
    url = f"https://{ALLOWED_HOST}/missing_segment.ts"

    mock_404 = urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    with patch("backend.hls_proxy.urllib.request.urlopen", side_effect=mock_404):
        resp = client.get(f"/api/hls/proxy?url={quote(url, safe='')}")

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "404" in detail or "HLS_PROXY_UPSTREAM_404" in detail


# ─────────────────────────────────────────────────────────────────────────────
# 6. Frontend proxy URL generation (Python-side equivalent)
# ─────────────────────────────────────────────────────────────────────────────

def test_build_proxy_url_encodes_correctly():
    remote = "https://g1o.empek.xyz/hls/live.m3u8?token=abc123"
    result = build_proxy_url(remote)
    assert result.startswith("/api/hls/proxy?url=")
    # The raw URL must not appear in the query string unencoded
    assert "g1o.empek.xyz" not in result.split("url=")[1] or "%" in result


def test_build_proxy_url_roundtrips():
    from urllib.parse import unquote, urlparse, parse_qs
    remote = "https://g1o.empek.xyz/hls/seg.ts"
    proxy_url = build_proxy_url(remote)
    qs = parse_qs(urlparse(proxy_url).query)
    decoded = unquote(qs["url"][0])
    assert decoded == remote


# ─────────────────────────────────────────────────────────────────────────────
# 7. /api/hls/proxy/info endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_proxy_info_endpoint_returns_allowlist():
    resp = client.get("/api/hls/proxy/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "allowed_hosts" in data
    assert "drogon.tv" in data["allowed_hosts"]
    assert "proxy_endpoint" in data


# ─────────────────────────────────────────────────────────────────────────────
# 8. Content-type helper
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected_ct", [
    ("https://cdn/index.m3u8", "application/vnd.apple.mpegurl"),
    ("https://cdn/seg000.ts", "video/mp2t"),
    ("https://cdn/seg.m4s", "video/mp4"),
    ("https://cdn/audio.aac", "audio/aac"),
    ("https://cdn/key.key", "application/octet-stream"),
    ("https://cdn/subs.vtt", "text/vtt"),
])
def test_content_type_for(url, expected_ct):
    assert _content_type_for(url) == expected_ct


# ─────────────────────────────────────────────────────────────────────────────
# 9. _is_playlist helper
# ─────────────────────────────────────────────────────────────────────────────

def test_is_playlist_true_for_m3u8():
    assert _is_playlist("https://cdn/live.m3u8") is True
    assert _is_playlist("https://cdn/live.m3u") is True


def test_is_playlist_false_for_segment():
    assert _is_playlist("https://cdn/seg.ts") is False
    assert _is_playlist("https://cdn/seg.m4s") is False


# ─────────────────────────────────────────────────────────────────────────────
# 10. Successful playlist proxy (mocked upstream)
# ─────────────────────────────────────────────────────────────────────────────

def test_proxy_returns_rewritten_m3u8_for_allowed_host():
    url = f"https://{ALLOWED_HOST}/hls/live.m3u8"

    mock_response = MagicMock()
    mock_response.read.return_value = SAMPLE_M3U8.encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("backend.hls_proxy.urllib.request.urlopen", return_value=mock_response):
        resp = client.get(f"/api/hls/proxy?url={quote(url, safe='')}")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/vnd.apple.mpegurl")
    body = resp.text
    # Segments must go through the proxy
    assert "/api/hls/proxy?url=" in body
    # Raw CDN host must not appear as a direct segment URL
    lines = [l.strip() for l in body.splitlines() if l.strip() and not l.startswith("#")]
    for line in lines:
        assert line.startswith("/api/hls/proxy"), (
            f"Segment line is not proxied: {line!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Existing TV tests still pass (smoke check)
# ─────────────────────────────────────────────────────────────────────────────

def test_tv_health_still_works():
    """Regression guard: existing /api/tv/health endpoint must still respond."""
    from unittest.mock import patch as _patch
    def fake_fetch(url, description):
        if "epg" in description.lower():
            return b"""<?xml version="1.0"?><tv></tv>"""
        return (
            b"#EXTM3U\n"
            b'#EXTINF:-1 tvg-id="test" group-title="Test",Test Channel\n'
            b"http://localhost:8080/test.m3u8\n"
        )
    with _patch("backend.tv_manager.fetch_drogon_data", fake_fetch):
        resp = client.get("/api/tv/health")
    assert resp.status_code == 200


def test_tv_channels_still_works():
    """Regression guard: existing /api/tv/channels endpoint must still respond."""
    from unittest.mock import patch as _patch
    def fake_fetch(url, description):
        return (
            b"#EXTM3U\n"
            b'#EXTINF:-1 tvg-id="test" group-title="Test",Test Channel\n'
            b"http://localhost:8080/test.m3u8\n"
        )
    with _patch("backend.tv_manager.fetch_drogon_data", fake_fetch):
        resp = client.get("/api/tv/channels")
    assert resp.status_code == 200
    channels = resp.json()
    assert isinstance(channels, list)
    assert len(channels) > 0
