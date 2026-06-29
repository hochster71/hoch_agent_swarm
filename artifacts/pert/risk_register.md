# Risk Register — HOCH Agent Swarm RC15

This register tracks schedule, operational, and security risks identified for the current release candidate cycle.

| Risk ID | Risk Description | Probability | Impact | Severity | Mitigation Strategy | Owner Role | Evidence Required |
|---|---|---|---|---|---|---|---|
| **RSK-001** | Docker Daemon socket crashes (OOM/CPU overload) | Medium | High | High | Rebuild containers cleanly before launch; limit parallel compose commands. | Docker Engineer | Successful `docker ps` and healthy app state |
| **RSK-002** | Stale screenshot manifest hash mismatches | Low | Medium | Low | Run screenshot capture inside worker and verify pytest output dynamically. | QA Engineer | `test_live_screenshot_manifest.py` passing |
| **RSK-003** | Nested HLS sub-playlist CORS blocker | High | High | High | Intercept and rewrite variant HLS `.m3u8` playlists recursively in Flask proxy. | TV Engineer | `test_tv_proxy_sub_playlist` passing |
| **RSK-004** | Private network address leakage / SSRF | Low | High | Medium | Enforce loops/loopback whitelist validation inside HLS segment fetching backend. | Security Auditor | Security review matrix check and pytest passing |
| **RSK-005** | Loss of context continuity on chat overflow | High | Medium | Medium | Write and maintain a static `CURRENT_STATE.md` file in the repo artifacts. | Swarm Manager | Validated `artifacts/handoff/CURRENT_STATE.md` |
