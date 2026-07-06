# Epic-Fury — Supabase Secret Rotation Runbook (T3, operator-only)

**Status:** OPEN BLOCKER for first monetized-app ship (handoff open-thread #2).
**Owner action required:** Self-heal correctly *cannot* un-leak a committed secret — only rotation
(invalidating the old value) closes the exposure. This is a **T3** action; HOCH will not perform it.

## The exposure

Two HIGH findings: hardcoded Supabase JWT tokens committed in

- `~/epic-fury-build/epic-fury-2026/docker-compose.yml`
- `~/epic-fury-build/epic-fury-2026/docker-compose.dev.yml`

These are **long-lived JWTs** (the `anon` and/or `service_role` keys). The `service_role` key bypasses
Row Level Security — anyone holding it has full read/write to the database. Because they are in git,
treat them as compromised even if the repo is private.

> Epic-Fury runs Supabase via `docker-compose` → this is a **self-hosted** deployment. The legacy
> self-hosted keys are *derived from a JWT secret you control*, so rotation here means **generate a new
> JWT secret and re-sign new anon + service_role keys**, then roll every service. (Supabase's hosted
> platform no longer rotates legacy keys and instead migrates you to publishable/secret keys — see
> "Forward path" below. Both are covered.)

## Pre-rotation (do first, ~5 min)

- [ ] **Stop the bleed to history isn't enough** — rotation is mandatory; note the old key values so you
      can confirm they stop working afterward.
- [ ] Inventory every place the old `anon` / `service_role` keys are used: both compose files, any
      `.env`, client bundles/mobile app config, CI secrets, edge functions, and any HOCH runtime that
      talks to this DB. You will update all of them in one window.
- [ ] Schedule a short maintenance window — self-hosted rotation restarts the Supabase stack.

## Rotation — self-hosted (docker-compose)

1. [ ] **Generate a new JWT secret** (≥ 32-char high-entropy random string):
       `openssl rand -base64 48` (store it in your secret manager, not in git).
2. [ ] **Mint new `anon` and `service_role` keys** signed with the new secret using Supabase's JWT
       generator (Self-Hosting docs → "Generate API Keys"), or the CLI/JWT tool with roles `anon` and
       `service_role`.
3. [ ] Put `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY` into a **`.env` that is git-ignored** (or a
       secret store / Docker secrets). **Do not** paste the values back into the compose YAML.
4. [ ] Change compose to read from env, e.g. `- JWT_SECRET=${JWT_SECRET}` /
       `- ANON_KEY=${ANON_KEY}` / `- SERVICE_ROLE_KEY=${SERVICE_ROLE_KEY}` in **both** the prod and dev
       files. Confirm `.env` (and `.env.*`) are in `.gitignore`.
5. [ ] Update Kong/PostgREST/Auth/Storage/Realtime and any Studio config that embeds the keys.
6. [ ] `docker compose down && docker compose up -d` (prod and dev). Watch logs for auth errors.
7. [ ] **Verify old keys are dead:** call the API with an OLD `service_role` key → expect 401/JWT
       error. Call with the NEW key → expect success. Screenshot both as evidence.

## Post-rotation

- [ ] Update every consumer from the inventory (clients, CI, edge functions, HOCH runtimes) to the new
      keys, then redeploy.
- [ ] **Purge the leaked values from git history** (they remain in old commits after you edit the file):
      `git filter-repo` (preferred) or BFG, then force-push and have collaborators re-clone. HOCH ships
      `scripts/purge_env_history.sh` for the env-file class.
- [ ] Re-run the HOCH self-heal / secret scan and the HASF Product Gate Verifier; the finding should
      clear to NO-GO→GO **only on real evidence** (old key rejected, no literal secret in tree/history).
- [ ] Add a recurrence guard: the repo pre-commit hook already blocks Stripe/private-key patterns —
      extend its pattern set to catch Supabase `service_role`/`anon` JWTs (a long `eyJ...` with
      `"role":"service_role"`), mirroring `tests/integration/test_no_literal_secrets.py`.

## Forward path (do this too, before Nov 2025 platform deadlines bite the hosted side)

Supabase is retiring the legacy `anon`/`service_role` model in favor of **publishable keys**
(`sb_publishable_...`, replaces `anon`) and **secret keys** (`sb_secret_...`, replaces `service_role`),
plus **asymmetric JWT signing keys** (zero-downtime, revocable per-key). If Epic-Fury ever moves to
hosted Supabase — or you want revocable keys without re-signing everything — migrate to the new keys and
signing keys rather than another symmetric-secret rotation.

## Definition of done (no fake-green)

Rotation is **not** done until: old `service_role` key returns 401 against the live API **(evidenced)**;
no Supabase JWT appears in the working tree **or** git history; every consumer uses the new keys; and
the self-heal scan + product gate pass on that real evidence.

## Sources

- [Rotating Anon, Service, and JWT Secrets — Supabase Docs](https://supabase.com/docs/guides/troubleshooting/rotating-anon-service-and-jwt-secrets-1Jq6yd)
- [Migrating to publishable and secret API keys — Supabase Docs](https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys)
- [JWT Signing Keys — Supabase Docs](https://supabase.com/docs/guides/auth/signing-keys)
- [Introducing JWT Signing Keys — Supabase Blog](https://supabase.com/blog/jwt-signing-keys)
- [API Key Rotation for Self-Hosted Supabase — Supascale](https://www.supascale.app/blog/api-key-rotation-for-selfhosted-supabase-a-complete-security)
- [Upcoming changes to Supabase API Keys — Discussion #29260](https://github.com/orgs/supabase/discussions/29260)
