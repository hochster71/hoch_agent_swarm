# Secrets & Deploy Discipline

**Authored 2026-07-16, after two same-day incidents that this doc exists to prevent.**

This is the standing rule set for how every HELM factory product ships and how the one
Stripe live secret is handled. It is enforced in code by `scripts/factory_deploy.sh` +
`coordination/products/products.json`. If you are about to deploy anything, this doc and
that script are the path — nothing ships outside it.

---

## 0. The two incidents this doc prevents (today, 2026-07-16)

1. **Wrong-folder deploy clobbered the live app.** A deploy was run from a *scaffold*
   folder that happened to be linked to the live `story-studio-live` Vercel project.
   `vercel deploy --prod` pushed the scaffold straight over the real app and it **404'd
   in production**. It was rolled back. Root cause: nothing verified that the folder you
   deploy *from* is the folder that product is *supposed* to come from, and the deploy
   went **directly to prod** with no preview/smoke gate.

2. **Stripe key skew across projects.** The live Stripe key existed in an
   inconsistent state across surfaces — an **expired key in one place** and an **empty
   env in another** — because the secret was being hand-pasted per project instead of
   stored once and injected. Result: checkout endpoints that look deployed but fail with
   "Expired API Key" / empty-env errors. A product that cannot mint a Stripe session is
   not sellable, no matter how green the dashboard looks (NO FAKE GREEN).

Both are the same failure family: **no single source of truth, and irreversible actions
with no gate in front of them.** The rules below close both.

---

## A. Secrets: one Stripe live key, one place, injected — never hand-pasted

### The rule
- There is **ONE** Stripe **live** secret key (`sk_live_…`) for the account
  (`acct_1Tdge9DINF9KNAIC`). It lives in **exactly one** secret store (the Vercel
  team-level environment variable / a single secrets manager entry), **never** in more
  than one place, **never** committed, **never** echoed, **never** hand-typed into each
  project's dashboard.
- Each Vercel project **references** that one secret (injected at build/runtime as
  `STRIPE_SECRET_KEY`). Projects do not each hold their own copy — copies drift, and
  drift is exactly what produced the "expired here / empty there" incident above.
- Price IDs, `STRIPE_WEBHOOK_SECRET`, `AUTH_SECRET`, `BASE_URL` follow the same
  discipline: defined once per product in one place, injected — not pasted per project.
- **Michael enters/pastes the secret himself, once, at the native prompt** (the
  `stripe login` / Vercel env prompt). Agents never store, echo, or hardcode it. That
  one-time paste IS the auth step, not a task list.

### Why "one place, injected" (not "paste per project")
When the same key is pasted into N project dashboards, rotating or fixing it means
editing N places, and any missed one silently fails at checkout. One canonical entry +
project references means **rotate once, everywhere picks it up**, and there is no
"expired in project A, empty in project B" skew.

### Rotation runbook (Stripe live key)
Do this whenever the key is suspected leaked, is expiring, or on a scheduled rotation.
Michael performs the auth/paste; the agent scripts everything around it.

1. **Create the new key.** In the Stripe Dashboard (live mode) → Developers → API keys →
   *Roll* the secret key, or create a new restricted key with the needed scopes. Copy the
   new `sk_live_…` **once**.
2. **Update the ONE canonical store.** Paste the new value into the single secrets entry
   (the team-level `STRIPE_SECRET_KEY`). Do **not** touch individual project copies —
   there should be none.
3. **Re-inject / redeploy references.** Trigger a redeploy of each product that
   references the secret so the new value is picked up. Every product uses
   `factory_deploy.sh`, so this is: for each affected `product_id`, run
   `scripts/factory_deploy.sh <product_id> --go` from its `source_of_truth`. The
   preview→smoke gate will *prove* the new key mints a real Stripe session before prod.
4. **Verify, don't assert.** The smoke test in `factory_deploy.sh` POSTs the product's
   `health_check` and requires a real `https://checkout.stripe.com/…` session URL and the
   **absence** of "Expired API Key" / "No such price". If any product still shows a
   failure signature, its reference wasn't updated — fix it before revoking the old key.
5. **Revoke the old key** only after every product's smoke test is green on the new key.
6. **Rotate the webhook secret too** if the endpoint changed; re-register the live
   webhook and re-run the smoke test.

---

## B. Deploy discipline: one repo → one project, preview→smoke→promote→rollback

### The rules
1. **One repo/source → one Vercel project.** Each product declares its single
   `source_of_truth` folder and its single `vercel_project` in `products.json`. That
   mapping is 1:1 and canonical.
2. **Never cross-link a scaffold to a live project.** A scaffold, experiment, or
   throwaway folder must **never** be `vercel link`-ed to a production project. This is
   the exact mistake that 404'd the live app. If a folder is not a product's declared
   `source_of_truth`, it may not deploy to that product's project — full stop.
3. **Never deploy straight to prod.** Deploys always go: **preview → smoke-test →
   promote → (auto-rollback on failure)**. `vercel deploy --prod` from a human/agent by
   hand is banned; the pipeline is the only path.
4. **Smoke-test before promote, fail-closed.** Preview must return HTTP 200 on the home
   path; sellable products must additionally return a real Stripe session URL from their
   `health_check` (no expired-key / no-such-price / 501 errors). No pass = no promote.
5. **Auto-rollback.** If the post-promote production check fails, roll back to the prior
   known-good deployment immediately and exit non-zero. Prod is never left broken.
6. **Every irreversible action is announced.** The pipeline prints an `[ACT]` line before
   each deploy/promote/rollback. Dry-run by default; irreversible steps require `--go`.
7. **NO FAKE GREEN.** A green dashboard is not proof. Proof is: source-match verified +
   preview smoke passed + post-promote prod verified. Report only what the evidence shows.

---

## C. How `factory_deploy.sh` + `products.json` enforce all of the above

**`coordination/products/products.json`** is the single source of truth. It is an array
of products; each entry carries:

| key | purpose |
|---|---|
| `product_id` | stable id, e.g. `HSF_STORY_STUDIO` |
| `source_of_truth` | the ONLY folder/repo this product may deploy **from** |
| `vercel_project` | the ONE Vercel project it maps to (1:1) |
| `live_url` | production URL to health-check |
| `health_check` | path; for sellable products, a checkout endpoint that must mint a Stripe session |
| `sellable` | bool — if true, the smoke test requires a real Stripe session URL |
| `owning_factory` | e.g. `HSF` |

**`scripts/factory_deploy.sh <product_id> [--go] [--source <dir>]`** is the only deploy path:

- **Source-match guard (the key safety).** It canonicalizes the current folder (or
  `--source`) and compares it to the product's declared `source_of_truth`. On mismatch it
  **aborts loudly** — *"refusing: source mismatch — this is how the live app got
  clobbered"* — and deploys nothing. A scaffold can no longer be pushed over a live
  project, because the folder must literally equal the declared source of truth.
- **Dry-run by default.** Without `--go` it runs the source-match guard + a read-only
  production health check and prints the exact plan. Nothing irreversible happens.
- **`--go` runs the gated pipeline:** `vercel deploy` to a **preview** (never `--prod`) →
  capture the preview URL → **smoke-test** it (home 200; sellable ⇒ real Stripe session,
  fail-closed against expired-key/no-such-price/501) → **promote** the preview to prod
  only if smoke passes → **re-verify prod** → **auto-rollback** to the prior deployment if
  that re-verify fails, exiting non-zero.
- **Announces irreversible actions** with `[ACT]` lines and is idempotent (it reads the
  manifest and live state; it does not mutate repo files).

Net effect: the wrong-folder clobber is structurally impossible (source-match guard), a
direct-to-prod push is impossible (preview→promote only), a broken prod self-heals
(auto-rollback), and a dead-key checkout can never be promoted (Stripe-session smoke
test). One key, one place, injected; one repo, one project, gated.
