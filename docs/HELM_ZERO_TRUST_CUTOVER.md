# HELM Zero-Trust Cutover Runbook (STAGED)

> **FOUNDER APPROVAL REQUIRED before any cutover step in this document is run.**
> Changing the bind address, adding TLS, or enabling read-auth are **security
> settings**. They can break phone access over Tailscale and the running 24 h
> Phase-C soak against `:8770`. Nothing in the `backend/security/zero_trust/`
> layer is auto-applied. It is staged and inert until a human, with founder
> sign-off, runs the commands below.

## 0. Why this exists — current posture (verified)

Run the read-only audit any time to re-derive posture:

```bash
python3 -m backend.security.zero_trust.bind_audit --out coordination/qa/swarm2/bind_audit_latest.json
```

Latest evidence: `coordination/qa/swarm2/bind_audit_*.json`. Findings (all
**OPEN — not remediated by this staged work**):

| # | Finding | Where | Control | Status |
|---|---------|-------|---------|--------|
| 1 | Live API binds `0.0.0.0` (all interfaces) | `scripts/helm_autoloop.sh:33` `uvicorn … --host 0.0.0.0 --port 8770` | SC-7, AC-4 | **OPEN (STAGED fix ready)** |
| 2 | Other services bind `0.0.0.0` | `docker/entrypoints/api.sh:5` (:8000), `scripts/remote_runtime/relay_api.py:78` (:8010) | SC-7 | **OPEN** |
| 3 | No TLS on origin | `:8770` is plain HTTP; Tailscale terminates HTTPS in front of a clear-text origin | SC-8 | **OPEN (STAGED fix ready)** |
| 4 | GET/read endpoints ungated | every `GET /api/v1/helm/*` in `backend/helm_live_api.py` | AC-3, IA-2 | **OPEN (STAGED fix ready)** |
| 5 | POST founder-decision path IS gated | `/api/founder/decide` → 401 on bad `HELM_FOUNDER_TOKEN` | IA-2, AC-3 | **CLOSED (pre-existing, verified)** |

Framework: **NIST SP 800-207 Zero Trust** (never trust the network; minimize the
boundary; authenticate every request) mapped to **NIST SP 800-53 Rev5** controls
above.

## 1. What the staged layer provides (NOT yet applied)

`backend/security/zero_trust/`:

- `config.py` — `HardenedConfig`, safe defaults (bind `127.0.0.1`, read-auth
  **off**, TLS **off**). Side-effect free.
- `read_auth.py` — `ReadAuthMiddleware`: read-token gate on GET, **disabled by
  default**, transparent passthrough until enabled. POST paths untouched.
- `dev_cert.py` — self-signed dev cert into `backend/security/zero_trust/_dev_certs/`
  (gitignored via a directory-local `.gitignore`; private key `chmod 600`, never
  committed).
- `bind_audit.py` — the fail-closed audit above.
- `staged_server.py` — the cutover launcher. Imports the **unmodified**
  `backend.helm_live_api:app` and wraps it. Refuses to bind `:8770` without an
  explicit `--staging-port`, and refuses to bind at all unless preflight passes
  and `--confirm` is given.

The live API source `backend/helm_live_api.py` is **not modified**.

## 2. Control mapping for each staged change

| Change | Env flag(s) | NIST control | 800-207 tenet |
|--------|-------------|--------------|---------------|
| Bind `127.0.0.1` / VPN iface, not `0.0.0.0` | `HELM_HARDENED_BIND_HOST` | SC-7 Boundary Protection, AC-4 Information Flow | Minimize the implicit trust zone |
| TLS termination (self-signed dev cert) | `HELM_TLS_ENABLED`, `HELM_TLS_CERT`, `HELM_TLS_KEY` | SC-8 Transmission Confidentiality & Integrity | Encrypt all traffic |
| Read-token gate on GET | `HELM_READ_AUTH_ENABLED`, `HELM_READ_TOKEN` | AC-3 Access Enforcement, IA-2 Identification & Auth | Authenticate every request |

## 3. Cutover procedure (run ONLY after founder approval)

### Pre-cutover (no impact on the live soak)

1. Announce a maintenance window. Confirm the Phase-C soak is either complete or
   the founder accepts the interruption. **Do not proceed during an unfinished
   soak without explicit go.**
2. Generate the dev cert (writes to a gitignored dir only):
   ```bash
   python3 -m backend.security.zero_trust.dev_cert
   ```
3. Provision the read token to every legitimate reader FIRST (the founder's phone,
   the wall browser, the Tailscale proxy header injection). Set it in the
   environment where the staged server will run:
   ```bash
   export HELM_READ_TOKEN="$(openssl rand -hex 32)"
   ```
4. Validate the hardened instance on a **separate staging port** (never `:8770`):
   ```bash
   HELM_HARDENED_BIND_HOST=127.0.0.1 \
   HELM_READ_AUTH_ENABLED=1 \
   HELM_TLS_ENABLED=1 \
   python3 -m backend.security.zero_trust.staged_server --staging-port 8781 --confirm
   ```
   Confirm: loopback bind, HTTPS handshake with the dev cert, GET without token →
   401, GET with token → 200, `/api/v1/helm/wall` still open, POST decide still
   gated by the founder token.

### Cutover (the only steps that touch the live service)

5. Stop the current `:8770` uvicorn started by `scripts/helm_autoloop.sh`. Because
   the autoloop auto-restarts the API, **first** stop/neutralize the autoloop
   (`com.hoch.helm-autoloop` launchd job) so it does not respawn the old
   plain-HTTP `0.0.0.0` process. *(This is a founder/operator action — this staged
   work never signals processes or touches launchd.)*
6. Update `scripts/helm_autoloop.sh` line 33 to launch via `staged_server` on
   `127.0.0.1:8770` with TLS + read-auth env set (use `guarded_edit`, holder
   `swarm/hardening`, since that file is shared).
7. Re-point the Tailscale serve route at the new origin scheme. If the origin is
   now HTTPS with a self-signed cert, use `tailscale serve --bg --https=443
   https+insecure://127.0.0.1:8770` (Tailscale trusts the loopback origin) — verify
   from the phone before declaring success.
8. Re-run the audit — expect the `:8770` config finding gone and origin TLS true:
   ```bash
   python3 -m backend.security.zero_trust.bind_audit
   ```

## 4. Phone-access & soak risk (read before touching anything)

- The founder reaches consoles **from his phone** over Tailscale `:443 → :8770`.
  If read-auth is enabled **before** the token reaches the phone, the phone gets
  401 on every panel. **Provision the token first (step 3).**
- The console/founder HTML is served same-origin from `:8770`. The HTML shell
  itself and `/api/v1/helm/wall` are on the read-auth allowlist so the page can
  load and health-probe; its data fetches must carry the token. Decide how the
  phone injects the header (proxy-side header injection is least disruptive).
- Switching the origin to loopback + HTTPS changes the Tailscale serve target. A
  wrong scheme (`http` vs `https+insecure`) silently breaks phone access — verify
  from the phone in the window, not after.
- The 24 h Phase-C soak reads/writes evidence, not the API bind, but restarting
  `:8770` interrupts any wall/observer polling and any liveness that depends on
  the API being up. Treat cutover as a soak-affecting event.

## 5. Rollback

1. Restore `scripts/helm_autoloop.sh` line 33 to the original
   `uvicorn backend.helm_live_api:app --host 0.0.0.0 --port 8770` (git revert the
   guarded edit).
2. Restore the original Tailscale route: `tailscale serve --bg --https=443
   http://127.0.0.1:8770`.
3. Unset `HELM_READ_AUTH_ENABLED` / `HELM_TLS_ENABLED`.
4. Re-enable the `com.hoch.helm-autoloop` job; confirm `api_up` and phone access.
5. Rollback is safe at any point because the live API source was never modified —
   reverting one launcher line and the Tailscale route fully restores prior state.

## 6. Approval gate

- [ ] Founder has approved bind-address change (SC-7/AC-4)
- [ ] Founder has approved TLS on origin (SC-8)
- [ ] Founder has approved read-auth on GET (AC-3/IA-2)
- [ ] Read token provisioned to phone + wall + proxy
- [ ] Maintenance window agreed; soak state accepted
- [ ] Rollback owner identified and on call

**Until every box is checked, the layer stays STAGED. No control above may be
reported as "closed" — only #5 (POST founder-token gate) is closed today, and it
predates this work.**
