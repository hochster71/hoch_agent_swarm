"""
backend/hls_proxy.py
====================
Server-side HLS proxy for Drogon.TV and related IPTV streams.

Motivation
----------
Browsers enforce the Same-Origin Policy: JavaScript running at
http://localhost:8085 cannot fetch https://g1o.empek.xyz/... directly
(CORS block) and upstream servers frequently reject browser User-Agent
strings with HTTP 403.  This module resolves both problems by fetching
every playlist / segment / key file on behalf of the browser and
forwarding the bytes through the trusted local backend origin.

Design rules
------------
* Fail-closed: any host NOT in HLS_ALLOWED_HOSTS → 403 immediately.
* Only GET; never write to upstream.
* Playlist (.m3u8) lines are rewritten so relative and absolute segment
  URLs all resolve back through this proxy.
* Content-Type is determined by the URL extension, not the upstream
  response header, so browsers never reject the payload.
* No caching layer here; the tv_manager already caches the playlist.
  Segments are streamed through in chunks.
"""

from __future__ import annotations

import os
import re
import urllib.request
import urllib.error
from typing import Optional
from urllib.parse import urlparse, urljoin, quote, unquote

from fastapi import HTTPException
from fastapi.responses import Response, StreamingResponse

# ---------------------------------------------------------------------------
# Host allowlist — edit this set to add/remove approved upstream hosts.
# Fail-closed: any host absent from this set is rejected with HTTP 403.
# ---------------------------------------------------------------------------
HLS_ALLOWED_HOSTS: frozenset[str] = frozenset(
    h.strip().lower()
    for h in os.getenv(
        "HLS_ALLOWED_HOSTS",
        ",".join([
            "g1o.empek.xyz",
            "empek.xyz",
            "drogon.tv",
            "www.drogon.tv",
            "cdn.drogon.tv",
            "stream.drogon.tv",
            "hls.drogon.tv",
            "iptv.drogon.tv",
        ]),
    ).split(",")
    if h.strip()
)

# Upstream request headers that mimic a real browser / media player.
_UPSTREAM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://drogon.tv",
    "Referer": "https://drogon.tv/",
    "Connection": "keep-alive",
}

# Chunk size when streaming binary segments.
_CHUNK_SIZE = 64 * 1024  # 64 KB

# Regex that matches absolute http(s) URLs inside .m3u8 playlists.
_ABS_URL_RE = re.compile(r"(https?://[^\s\r\n\"']+)", re.IGNORECASE)

# Lines that are definitely not media URIs (directives, comments, …).
_M3U8_TAG_RE = re.compile(r"^\s*#")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_host_allowed(url: str) -> bool:
    """Return True iff the URL's host is in HLS_ALLOWED_HOSTS."""
    try:
        host = urlparse(url).hostname or ""
        return host.lower() in HLS_ALLOWED_HOSTS
    except Exception:
        return False


def build_proxy_url(remote_url: str, base_path: str = "/api/hls/proxy") -> str:
    """Return the local proxy URL for *remote_url*."""
    return f"{base_path}?url={quote(remote_url, safe='')}"


def _content_type_for(url: str) -> str:
    """Derive the correct Content-Type from the URL path extension."""
    path = urlparse(url).path.lower().split("?")[0]
    if path.endswith(".m3u8") or path.endswith(".m3u"):
        return "application/vnd.apple.mpegurl"
    if path.endswith(".ts"):
        return "video/mp2t"
    if path.endswith(".m4s") or path.endswith(".mp4"):
        return "video/mp4"
    if path.endswith(".m4v"):
        return "video/x-m4v"
    if path.endswith(".aac"):
        return "audio/aac"
    if path.endswith(".mp3"):
        return "audio/mpeg"
    if path.endswith(".vtt"):
        return "text/vtt"
    if path.endswith(".key") or path.endswith(".pem"):
        return "application/octet-stream"
    # Fallback — browsers can still handle this
    return "application/octet-stream"


def _is_playlist(url: str) -> bool:
    path = urlparse(url).path.lower().split("?")[0]
    return path.endswith(".m3u8") or path.endswith(".m3u")


def _rewrite_playlist(content: str, remote_url: str) -> str:
    """
    Rewrite a downloaded .m3u8 so that every segment / sub-playlist URL
    becomes a relative reference through /api/hls/proxy?url=<encoded>.

    Handles:
    * Absolute http(s) URLs anywhere on non-comment lines
    * Absolute http(s) URLs inside EXT-X-KEY URI="…" attributes
    * Relative paths (resolved against the playlist's own base URL)
    """
    base = remote_url  # used to resolve relative paths

    lines = content.splitlines(keepends=True)
    out: list[str] = []

    for line in lines:
        stripped = line.rstrip("\r\n")

        # ── Comment / tag lines ────────────────────────────────────────────
        if stripped.startswith("#"):
            # Rewrite URI attributes inside EXT-X-KEY, EXT-X-MAP, etc.
            def _rewrite_uri_attr(m: re.Match) -> str:
                uri_str = m.group(1)
                # Strip surrounding quotes
                inner = uri_str.strip("\"'")
                resolved = _resolve(inner, base)
                if resolved and is_host_allowed(resolved):
                    proxied = build_proxy_url(resolved)
                    # Keep the same quote style
                    if uri_str.startswith('"'):
                        return f'URI="{proxied}"'
                    return f"URI='{proxied}'"
                return m.group(0)

            new_line = re.sub(r'URI=(["\'][^"\']+["\'])', _rewrite_uri_attr, stripped)
            # Also rewrite bare absolute URLs inside tags (e.g. EXT-X-MEDIA)
            new_line = _ABS_URL_RE.sub(_rewrite_abs_url, new_line)
            out.append(new_line + "\n")

        # ── Blank lines ────────────────────────────────────────────────────
        elif not stripped:
            out.append(line)

        # ── Segment / sub-playlist lines ───────────────────────────────────
        else:
            resolved = _resolve(stripped, base)
            if resolved:
                if is_host_allowed(resolved):
                    out.append(build_proxy_url(resolved) + "\n")
                else:
                    # Fail-closed: substitute a marker the player will skip
                    out.append(
                        f"# HLS_PROXY_BLOCKED_HOST: {stripped}\n"
                    )
            else:
                # Unable to resolve — pass through unchanged
                out.append(line)

    return "".join(out)


def _rewrite_abs_url(m: re.Match) -> str:
    """Regex replacement callback: rewrite absolute URL → proxy URL."""
    url = m.group(1)
    if is_host_allowed(url):
        return build_proxy_url(url)
    return url  # leave unrecognised hosts untouched


def _resolve(path: str, base_url: str) -> Optional[str]:
    """Resolve *path* relative to *base_url*.  Returns None on failure."""
    try:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(base_url, path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# FastAPI request handler
# ---------------------------------------------------------------------------

def proxy_hls_asset(url: str) -> Response:
    """
    Main handler for GET /api/hls/proxy?url=<encoded_url>.

    1. Validate host against allowlist → 403 if blocked.
    2. Fetch the remote asset with browser-like headers.
    3. If playlist: rewrite all segment URLs through the proxy; return as
       application/vnd.apple.mpegurl.
    4. If segment/key: stream the bytes through with the correct MIME type.
    """
    # ── 1. Decode & validate ───────────────────────────────────────────────
    raw_url = unquote(url)
    if not raw_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="HLS_PROXY_ERROR: URL must start with http:// or https://",
        )

    if not is_host_allowed(raw_url):
        raise HTTPException(
            status_code=403,
            detail=(
                f"HLS_PROXY_BLOCKED: host '{urlparse(raw_url).hostname}' "
                "is not in the approved upstream allowlist."
            ),
        )

    # ── 2. Fetch upstream ─────────────────────────────────────────────────
    req = urllib.request.Request(raw_url, headers=_UPSTREAM_HEADERS)
    try:
        upstream_resp = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise HTTPException(
                status_code=502,
                detail=(
                    "HLS_PROXY_UPSTREAM_403: The upstream server refused the request "
                    f"for {urlparse(raw_url).hostname} (HTTP 403). "
                    "The stream may require a valid subscription or the URL may have expired."
                ),
            )
        if exc.code == 404:
            raise HTTPException(
                status_code=404,
                detail=(
                    "HLS_PROXY_UPSTREAM_404: The requested HLS asset was not found "
                    f"on the upstream server ({exc.code}). The segment or playlist "
                    "may have expired from the origin CDN."
                ),
            )
        raise HTTPException(
            status_code=502,
            detail=f"HLS_PROXY_UPSTREAM_ERROR: HTTP {exc.code} from upstream.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"HLS_PROXY_NETWORK_ERROR: {exc}",
        )

    content_type = _content_type_for(raw_url)

    # ── 3. Playlist rewrite ───────────────────────────────────────────────
    if _is_playlist(raw_url):
        try:
            raw_bytes = upstream_resp.read()
            playlist_text = raw_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"HLS_PROXY_PLAYLIST_READ_ERROR: {exc}",
            )

        try:
            rewritten = _rewrite_playlist(playlist_text, raw_url)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"HLS_PROXY_REWRITE_ERROR: Failed to rewrite playlist: {exc}",
            )

        headers = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
            "X-HLS-Proxy": "rewritten",
        }
        return Response(
            content=rewritten.encode("utf-8"),
            media_type=content_type,
            headers=headers,
        )

    # ── 4. Binary segment / key passthrough ──────────────────────────────
    def _stream():
        try:
            while True:
                chunk = upstream_resp.read(_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream_resp.close()

    return StreamingResponse(
        _stream(),
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
            "X-HLS-Proxy": "segment",
        },
    )
