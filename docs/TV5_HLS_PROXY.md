# TV5 — Local HLS Proxy and UI Health Stability

The Local HLS Proxy (TV5) handles CORS issues when loading remote HLS IPTV streams in browser players. Instead of connecting directly to external stream endpoints, the frontend requests playlists and segment chunks through the local Flask backend.

## Compliance Notice & Status Boundary

> [!IMPORTANT]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> 
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated, and no claim of absolute security is made.*

## Feature Overview

1. **Local Playlist Rewriting**: Fetches `.m3u8` master playlists from remote sources, parses inline stream declarations, and rewrites URI attributes (e.g., `URI="..."`) and segment URLs to route through the local proxy backend.
2. **Local Chunk Proxy**: Downloads HLS video/audio segments (e.g. `.ts` chunks) on behalf of the client, bypassing browser CORS policies.
3. **SSRF Prevention & Security Controls**: Restricts proxying to trusted hosts only:
   - Rejects loopback addresses (`127.0.0.1`, `localhost`, `::1`).
   - Rejects link-local metadata endpoints (`169.254.169.254`).
   - Restricts external segment fetches to matching playlist domains or a strict whitelist of known IPTV providers (`bitdash-a.akamaihd.net`, `demo.unified-streaming.com`, `sample.vodobox.com`).
4. **Degraded Health Status Recovery**: Handles backend disconnects in the UI gracefully by displaying a prominent warning card and throttling console error logs.

---

## Technical Mechanisms

### 1. Playlist URL Parsing & Rewriting
When the browser requests a channel's master playlist, the backend:
- Fetches the remote `.m3u8` playlist text.
- Parses all absolute and relative URLs.
- Appends query parameters to relative paths if the playlist URL had queries.
- Encodes URLs into a hex string to avoid raw URL character issues in request paths.
- Replaces remote references with local endpoints: `/api/tv/stream/<channel_id>/asset?url=<hex_encoded_url>`.

### 2. Segment Whitelisting & Loopback Prevention
The proxy filters all requested assets through `fetch_hls_asset` to ensure compliance:
- Validates the target host name.
- Blocks metadata/SSRF attempts.
- Verifies that target domains match the channel's playlist domain, or match a validated IPTV template.

---

## API Endpoints

The Flask UI server exposes the following endpoints under `/api/tv/stream/`:

- `GET /api/tv/stream/<channel_id>/master.m3u8`: Fetches and rewrites the master HLS playlist for a channel.
- `GET /api/tv/stream/<channel_id>/asset?url=<hex_encoded_url>`: Proxies HLS media chunks and child playlists.

---

## Diagnostic Checklist

1. **Verify M3U Stream Availability**: Verify that the remote channel URL is reachable from the server host.
2. **Inspect Rewritten Playlists**: Open `/api/tv/stream/<channel_id>/master.m3u8` in a browser or curl to ensure all URIs point to `/api/tv/stream/.../asset?url=`.
3. **Check SSRF Violations**: Attempting to proxy `http://127.0.0.1` should result in a `403 Forbidden` response.
