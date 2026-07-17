# HELM LIVE API — Hardening (R-AUTH / R-CORS remediation)

Remediates the two mission-assurance audit findings against the HELM LIVE API
(`backend/helm_live_api.py`, uvicorn `:8770`):

1. **R-AUTH** — an unauthenticated sensitive GET/POST surface.
2. **R-CORS** — a permissive `allow_origins="*"` control plane.

**Everything below is FLAGGED and default-OFF.** With no new env vars set, the API
behaves exactly as it does today — the running server and the founder's open
dashboards do **not** break. Activation is a deliberate founder act (set the env
vars, then restart the server).

---

## What changed

| Area | Change | Default |
|------|--------|---------|
| CORS | Origin **allowlist** (never `*`), env-driven, optional `*.ts.net` | Safe loopback set |
| AuthN/AuthZ | Deny-by-default **bearer-token gate** on the sensitive API surface | **OFF** |
| Payload size | Reject oversized request bodies (413) | 2 MB, always on |
| Rate limiting | Per-IP fixed-window limiter on `/api/*` | **OFF** |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | Always on |

New code:

- `backend/security/api_hardening.py` — the CORS resolver + `ApiHardeningMiddleware`.
- `backend/helm_live_api.py` — CORS block now uses the resolver; the middleware is
  mounted as the outermost layer.
- `tests/test_helm_live_api_security.py` — 16 tests (all passing).

This layer is **independent of** and coexists with the pre-existing
`ReadAuthMiddleware` (`HELM_READ_AUTH_ENABLED`). Both are default-OFF; you can use
either or both.

### Which routes are gated when auth is ON

- **Gated (require bearer token):** all `/api/v1/helm/*` data endpoints, the
  `/api/helm/*` aliases, and every mutating (`POST/PUT/PATCH/DELETE`) API route.
- **Open (no token):**
  - `/api/helm/live` — liveness/health probe.
  - The static UI pages (`/`, `/brain`, `/roadmap`, `/command`, `/console`,
    `/pert`, `/founder`, `/voice`, `/mission`, …) and JS helpers — so a page can
    load and then attach the token to its data fetches.
  - `/api/founder/queue` and `/api/founder/decide` — these keep their **own**
    founder-token gate (`HELM_FOUNDER_TOKEN`); the API bearer is not layered on
    top so the iPhone approval flow is unaffected.

A denied request gets a clean `401` JSON body (`{"state":"UNAUTHORIZED", ...}`)
with no internal detail leaked.

---

## Env vars

| Variable | Purpose | Default |
|----------|---------|---------|
| `HELM_REQUIRE_AUTH` | `1` to enable the bearer gate | unset (OFF) |
| `HELM_API_TOKEN` | the expected bearer token (**secret — never commit**) | unset |
| `HELM_CORS_ALLOWLIST` | comma-separated CORS origins | falls back to `HELM_CORS_ORIGINS`, then loopback default |
| `HELM_CORS_ALLOW_TSNET` | `1` to also allow `*.ts.net` (Tailscale) origins | unset |
| `HELM_RATE_LIMIT_ENABLED` | `1` to enable the per-IP limiter | unset (OFF) |
| `HELM_RATE_LIMIT_RPM` | requests/minute/IP | `600` |
| `HELM_MAX_BODY_BYTES` | max request body size | `2000000` (2 MB) |

Notes:
- If `HELM_REQUIRE_AUTH=1` but `HELM_API_TOKEN` is empty, the gate **fails closed**
  (401 for everything gated) — it never fails open.
- CORS never emits `*`; `allow_credentials` is `False`.
- Callers authenticate with `Authorization: Bearer <HELM_API_TOKEN>`.

---

## Founder activation (do this to turn it ON)

Auth is not scriptable to completion because it requires **your** secret token —
the script below pauses for you to paste it at a hidden prompt; nothing is stored
or echoed. Then you restart the server yourself.

```bash
# 1) Generate + paste a token at a HIDDEN prompt (not stored, not echoed).
read -rs -p "Paste a strong HELM_API_TOKEN (e.g. output of: openssl rand -hex 32): " HELM_API_TOKEN; echo
export HELM_API_TOKEN
export HELM_REQUIRE_AUTH=1

# 2) Lock CORS to exactly the origins you use (adjust to your real hosts).
export HELM_CORS_ALLOWLIST="https://127.0.0.1:8770,http://127.0.0.1:8770"
export HELM_CORS_ALLOW_TSNET=1     # optional: allow your Tailscale *.ts.net host

# 3) (optional) turn on rate limiting
# export HELM_RATE_LIMIT_ENABLED=1

# 4) Restart the server (you do this — Claude does not restart :8770).
#    Re-launch uvicorn against backend.helm_live_api:app the same way you do now,
#    with the env above exported in that shell.
```

**After activation, the dashboards need the token.** Any browser/console hitting
the gated `/api/v1/helm/*` endpoints must send `Authorization: Bearer <token>`.
The HTML shells still load without it; wire the token into their fetch calls
(the existing `frontend_live/helm_auth.js` helper is the intended place).

Verify quickly after restart:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8770/api/v1/helm/pert           # -> 401
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $HELM_API_TOKEN" \
     http://127.0.0.1:8770/api/v1/helm/pert                                                # -> 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8770/api/helm/live               # -> 200 (health stays open)
```

## Tests

```bash
python -m pytest tests/test_helm_live_api_security.py -v
# 16 passed
```
