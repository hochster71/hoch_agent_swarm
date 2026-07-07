# Apple Calendar CalDAV Adapter

A production-grade, **security-first**, **local-only** adapter that lets the
Hoch Agent Swarm read (and, only under explicit approval, write) the user's
Apple / iCloud Calendar over CalDAV.

> **Status: NOT fully integrated.** This service is code-complete and passes its
> offline security + redaction test suites, but **full integration is not
> considered done until a live iCloud discovery call succeeds** (`GET
> /apple/calendars` returns real calendars) during the Phase 1 rollout below.

---

## 1. Architecture

```
                 127.0.0.1:8011  (loopback ONLY — never 0.0.0.0)
                        │
              ┌─────────▼──────────┐
              │   FastAPI (app.py) │
              │  structured JSON    │
              └───┬─────────┬───────┘
   read paths     │         │   write paths (gated)
 ┌────────────────▼──┐   ┌──▼───────────────────────────┐
 │ /health           │   │ /apple/events/dry-run  (safe) │
 │ /apple/calendars  │   │ /apple/events    (POST, gated)│
 │ /apple/events     │   │ PATCH/DELETE  (DISABLED, 403) │
 └─────────┬─────────┘   └──────────────┬────────────────┘
           │                            │
   ┌───────▼────────┐          ┌────────▼─────────┐
   │ redaction.py   │          │ evaluate_write_  │
   │ (titles/times; │          │ gate() FAIL-CLOSED│
   │ bodies hidden) │          └────────┬─────────┘
   └───────┬────────┘                   │ record BEFORE execute
           │                   ┌─────────▼──────────┐
   ┌───────▼────────┐          │ ledger.py (SQLite) │
   │ caldav (lazy)  │◄─────────┤ append-only audit  │
   │ iCloud CalDAV  │          └────────────────────┘
   └────────────────┘
```

Files:

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app + pure security-gate functions (`resolve_mode`, `get_credentials`, `evaluate_write_gate`, `build_ics`). `fastapi`/`caldav` imported lazily so the module is import-clean offline. |
| `models.py` | Pydantic request models. `start < end` validated via `datetime.fromisoformat`. |
| `redaction.py` | Pure functions: `redact_secret`, `redact_event`. No third-party deps. |
| `ledger.py` | SQLite append-only audit ledger (`apple_calendar_ledger.sqlite3`). |
| `requirements.txt` | Pinned runtime deps. |
| `.env.example` | Placeholder env. **No real secret.** |

---

## 2. Security model

Hard rules, enforced in code:

1. **Secret never leaves the process.** The app-specific password
   (`APPLE_CALDAV_PASSWORD`) is never logged, printed, returned, or embedded.
   Every error string is passed through `redact_secret()`, which scrubs the
   live secret value. `Credentials.redacted()` is the only representation that
   crosses a boundary, and it masks the password.
2. **Bodies are redacted by default.** `redact_event()` drops event
   `description`/`body`/`notes` unless the caller is explicitly `approved`.
   Only titles + times are exposed by default.
3. **Loopback only.** The server binds `127.0.0.1:8011`. Never `0.0.0.0`.
4. **Read-only by default.** `APPLE_CALENDAR_MODE` defaults to `read_only`.
   A write is accepted **only** when `mode == read_write` **AND** an
   `approval_token` or `approved=true` is present (`evaluate_write_gate`).
5. **Fail closed.** Missing/ambiguous credentials, calendar, or approval raise
   `SecurityError` (pre-redacted) → HTTP 4xx/5xx. Nothing is guessed.
6. **Audit before action.** Every mutating attempt is written to the ledger
   **before** execution; the result (hash only, never the body) is updated
   after. Denied attempts are also recorded.
7. **PATCH/DELETE disabled.** Scaffolded but return `403 "write disabled"`.

---

## 3. Credential setup — Keychain first

The adapter resolves the password at runtime in this order:

1. **macOS Keychain** (preferred):

   ```bash
   security add-generic-password \
     -a "hochster_71@mac.com" \
     -s "hoch-agent-swarm-apple-caldav" \
     -w   # you will be prompted for the app-specific password (hidden)
   ```

   Generate the **app-specific password** at <https://account.apple.com>
   (Sign-In & Security → App-Specific Passwords). Do **not** use your main
   Apple ID password.

2. **Environment fallback** (`.env`, exported at runtime only):

   ```bash
   export APPLE_CALDAV_USERNAME="hochster_71@mac.com"
   export APPLE_CALDAV_PASSWORD="xxxx-xxxx-xxxx-xxxx"   # app-specific pw
   export APPLE_CALDAV_HOST="https://caldav.icloud.com"
   ```

The value is **never** written to disk by this service and **never** appears in
`.env.example`.

---

## 4. Run + verify

Install into an isolated venv (do this yourself; the task does not install):

```bash
python3 -m venv .venv-apple && source .venv-apple/bin/activate
pip install -r services/apple_calendar_adapter/requirements.txt
```

Run:

```bash
bash scripts/run_apple_calendar_adapter.sh
# -> uvicorn on http://127.0.0.1:8011
```

Verify (offline security + redaction tests + py_compile):

```bash
bash scripts/verify_apple_calendar_adapter.sh   # exit 0 only if all pass
```

Smoke-test once running:

```bash
curl -s http://127.0.0.1:8011/health
# {"status":"ok"}

curl -s "http://127.0.0.1:8011/apple/calendars"   # live iCloud discovery
```

---

## 5. Phase 1 rollout (read-only) + GO/NO-GO gate

**Phase 1 — read-only.**

1. Configure the Keychain entry (section 3).
2. Keep `APPLE_CALENDAR_MODE=read_only`.
3. Start the adapter; confirm `GET /health` → ok.
4. **GO/NO-GO gate:** run `GET /apple/calendars`.
   - **GO** if it returns your real iCloud calendars (live discovery succeeds).
   - **NO-GO** on any auth error, empty result, or timeout — fix credentials /
     connectivity before proceeding. Do **not** enable writes.
5. Exercise `GET /apple/events?start=...&end=...` and confirm descriptions are
   hidden (only titles/times) unless `approved=true`.

**Phase 2 — writes (only after Phase 1 GO).** Set
`APPLE_CALENDAR_MODE=read_write` and pass `approved=true` (or an
`approval_token`) per request. Every write is logged to the ledger first.

> Until the Phase 1 GO/NO-GO gate passes with a **successful live iCloud
> discovery**, this integration is **incomplete**.
