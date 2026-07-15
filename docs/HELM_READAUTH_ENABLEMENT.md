# Read-Auth Enablement (AC-3 / IA-2) — the final Zero-Trust flip

> **Run this AFTER Phase C seals `SOAK_PHASE_C_PASS`.** It restarts the API, which
> interrupts a running soak. Doing it mid-soak throws away the run. The build is
> already loopback+TLS+single-supervisor; this adds the read-token gate on GET.

Status of the pieces (all built + validated on staging port :8782):
- `ReadAuthMiddleware` gates GET, fail-closed, transparent when disabled.
- `frontend_live/helm_auth.js` attaches the token on `/api` GETs, prompts once on 401.
  Wired into all 7 consoles; served at `/frontend_live/helm_auth.js`.
- Allowlist covers the HTML shells + helper + `/wall`, so pages load then attach the token.

## Prerequisite (do FIRST, before flipping — else the phone gets 401 on every panel)
Provision a durable read token into the launchd session so the API inherits it, and
have it ready to type into the phone:
```bash
launchctl setenv HELM_READ_TOKEN "$(openssl rand -hex 32)"
# copy the value you'll enter on the phone:
launchctl getenv HELM_READ_TOKEN        # (visible only in YOUR terminal; keep it private)
```

## The flip (operator-run — Claude does not flip live security settings)
1. Point the autoloop's `start_api()` at the hardened launcher instead of plain uvicorn.
   In `scripts/helm_autoloop.sh`, the current cutover launch is:
   ```
   uvicorn backend.helm_live_api:app --host 127.0.0.1 --port 8770 --ssl-certfile ... --ssl-keyfile ...
   ```
   Replace it with the read-auth-enabled staged server (loopback + TLS + read-auth):
   ```
   HELM_HARDENED_BIND_HOST=127.0.0.1 HELM_READ_AUTH_ENABLED=1 HELM_TLS_ENABLED=1 \
   HELM_TLS_CERT="$HOME/.helm/dev_certs/helm_dev_cert.pem" \
   HELM_TLS_KEY="$HOME/.helm/dev_certs/helm_dev_key.pem" \
   "$PY" -m backend.security.zero_trust.staged_server --staging-port 8770 --confirm
   ```
   (`HELM_READ_TOKEN` comes from the launchd env set above — never written in this file.)
   Claude will prepare this exact edit for your review under `guarded_edit`.
2. Restart so it takes effect:
   ```bash
   pkill -f "uvicorn backend.helm_live_api:app"; pkill -f "staged_server --staging-port 8770"
   launchctl kickstart -k gui/$(id -u)/com.hoch.helm-autoloop
   ```
3. Verify (loopback, no token → 401; with token → 200; shells still load):
   ```bash
   curl -sk https://127.0.0.1:8770/command -o /dev/null -w "shell:      %{http_code}\n"     # 200
   curl -sk https://127.0.0.1:8770/api/v1/helm/chain -o /dev/null -w "no-token:   %{http_code}\n"   # 401
   curl -sk -H "Authorization: Bearer $HELM_READ_TOKEN" https://127.0.0.1:8770/api/v1/helm/chain -o /dev/null -w "with-token: %{http_code}\n"  # 200
   ```
4. On the **phone**: open a console → it prompts "HELM read token required" → paste the
   token → stored in localStorage → all panels load thereafter.

## Internal-reader risk — CHECKED, clear (2026-07-15)
Any INTERNAL component that reads a gated `/api/*` GET over HTTP would 401 when the
gate turns on. Swept `backend/` + `scripts/` for HTTP reads of `:8770`:
- `helm_autoloop.sh` health check hits `/wall` — **allowlisted, fine.**
- `backend/voice/router.py` builds `:8770` URL *strings* for display — it does NOT
  fetch them, so no 401.
- `scripts/validation/validate_mission_state_independent.py` (Grok's on-demand harness)
  uses plain `http://…:8770`; it is not a live component. If you run it against a
  read-auth'd API, point `HELM_VALIDATE_BASE` at `https://…` and pass the token.
Conclusion: **no live internal HTTP reader of a gated endpoint — the flip is safe.**
Voice is currently DISABLED; if you later enable it and it self-fetches gated data,
give it the token or allowlist its paths.

## Rollback
Revert the `helm_autoloop.sh` launch line to the plain loopback+TLS uvicorn (git),
`launchctl unsetenv HELM_READ_TOKEN`, restart. The live API source is never edited.
