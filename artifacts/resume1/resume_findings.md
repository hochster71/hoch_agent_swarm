# Resume Findings — RESUME1

During context recovery and verification, we identified a critical playback issue with HOCH TV CORS-free streaming.

## Findings

### 1. Nested HLS Sub-Playlist Direct Load (CORS Blocker)
- **Classification**: Medium
- **Description**: The master HLS playlist was correctly rewritten to proxy all URLs through `/api/tv/stream/<channel_id>/asset?url=<hex>`. However, the sub-playlists (variant playlists like `ch65.m3u8`) themselves were not rewritten upon being fetched by the proxy. As a result, the browser player loaded the sub-playlist raw and attempted to resolve the media segments directly to the remote stream domain (`https://g1o.empek.xyz`), violating CORS policies.
- **Fix**: Updated `/api/tv/stream/<channel_id>/asset` in `src/hoch_agent_swarm/ui_server.py` to recursively decode, rewrite, and serve nested `.m3u8` sub-playlists through the local loopback proxy.
- **Verification**: Added `test_tv_proxy_sub_playlist` to `tests/test_tv.py` to verify that variant playlists are correctly processed and rewritten.
