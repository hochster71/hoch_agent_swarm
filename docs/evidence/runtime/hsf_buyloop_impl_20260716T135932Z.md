# HSF Story Studio — Buy-Loop Implementation Evidence

**Authored (UTC):** 2026-07-16T13:59:32Z
**Scope:** `hsf/deploy/` only. No Python backend, soak, agent_executor, ledgers, or DB touched.
**Doctrine:** NO FAKE GREEN. This is a **LOGIC-LEVEL, TEST-MODE verification with MOCKED Stripe + in-memory store**. It is **NOT** a live run and **NOT** a real Stripe test-mode run (which would require founder keys + network). Every claim is bound to a file.

---

## 1. What this delivers

Made the `checkout → webhook → entitlement` loop **code-complete and coherent end-to-end** so it can run locally and in tests **without any credentials**, and resolved the two blockers called out in the build spec (`docs/factories/products/HSF_story_studio_checkout_spec.md` §2):

- `hsf/deploy/lib/store.js` was **missing**, so `api/webhook.js` threw `MODULE_NOT_FOUND` on the first paid event. **Now implemented.**
- Several `api/*` routes referenced by `vercel.json` / `hsf/story-studio-v2.html` did not exist. **Now present** (real where the loop needs them, clearly-marked STUB otherwise), so the deploy manifest has no dangling routes.

---

## 2. Files created / modified

| File | Kind | Notes |
|---|---|---|
| `hsf/deploy/lib/store.js` | **REAL** | KV wrapper. `@vercel/kv` when `KV_REST_API_URL`+`KV_REST_API_TOKEN` present; **in-memory `Map` fallback** with no creds. Lazy+guarded require so absent package never crashes. |
| `hsf/deploy/api/entitlement.js` | **REAL** | `GET /api/entitlement?storyId=…&email=…` → `{ paid, tier, source }`. Reads `story:<id>` / `email:<addr>`. Fails open-safe (200 `{paid:false}`). |
| `hsf/deploy/api/export.js` | **REAL gate + STUB body** | Real entitlement gate: `402` when unpaid; `501 not_implemented(stub)` once entitled (hosting/render not wired). |
| `hsf/deploy/api/download.js` | **REAL gate + STUB body** | Same gate pattern; file delivery is STUB. |
| `hsf/deploy/api/art.js` | **REAL gate + STUB body** | `402` unpaid, else `501` (no image model). |
| `hsf/deploy/api/save-story.js` | **STUB** | `501 not_implemented`. |
| `hsf/deploy/api/share.js` | **STUB** | `501 not_implemented`. |
| `hsf/deploy/api/morph.js` | **STUB** | `501 not_implemented`. |
| `hsf/deploy/api/story-brief.js` | **STUB** | `501` (no language model). |
| `hsf/deploy/api/auth/request-link.js` | **STUB** | `501` (needs `AUTH_SECRET` + mailer). |
| `hsf/deploy/api/auth/verify.js` | **STUB** | `501 not_implemented`. |
| `hsf/deploy/package.json` | **NEW** | CommonJS (no `"type":"module"`, matches existing `module.exports`/`require` functions). `"test": "node --test"`. Declares `stripe` + `@vercel/kv` as deps but tests **do not install or need them** (mocked). |
| `hsf/deploy/test/buyloop.test.js` | **NEW** | `node:test` + `node:assert`, Stripe + KV mocked at loader level. |

Existing files (`create-checkout-session.js`, `webhook.js`, `pricing.config.json`, `vercel.json`, `.env.example`, `README.md`) were **read, not modified**.

---

## 3. store.js interface — matched to webhook.js (line refs)

`api/webhook.js` imports (verified against source):

- `const { setPaid, put } = require('../lib/store');` — **L107**
  - `setPaid('email:' + email, { tier, sessionId })` — **L111**; `put('cust:' + customer, { email })` — **L113**; `setPaid('story:' + storyId, {...})` — **L115**
- `const { setUnpaid, get } = require('../lib/store');` — **L122**
  - `get('cust:' + customer)` — **L123**; `setUnpaid('email:' + email)` — **L124**
- `const { setPaid, setUnpaid, get } = require('../lib/store');` — **L131** (subscription.updated)

Implemented signatures in `lib/store.js` (exact match, all async):
`get(key)→value|null`, `put(key,value)`, `setPaid(key,meta)`, `setUnpaid(key)`, plus `isPaid(key)→bool` (used by entitlement/gates) and `_reset()` (test-only). Keys `story:<id>`, `email:<addr>`, `cust:<id>` as the webhook implies.

---

## 4. Routes: referenced set vs. real/STUB

Front-end (`hsf/story-studio-v2.html`) calls: `/api/story-brief` (L268), `/api/create-checkout-session` (L375), `/api/auth/request-link` (L390), `/api/export` (L407), `/api/art` (L424), `/api/entitlement` (L655).
`vercel.json` additionally lists: `save-story`, `download`, `webhook`, `auth/verify`, `share`, `morph`.

- **REAL (buy loop):** `create-checkout-session` (pre-existing), `webhook` (pre-existing, now unblocked by store), `entitlement`, `lib/store`.
- **REAL entitlement gate, STUB body:** `export`, `download`, `art`.
- **STUB (`501 not_implemented`, commented as such):** `save-story`, `share`, `morph`, `story-brief`, `auth/request-link`, `auth/verify`.

No route dangles in `vercel.json`; no STUB pretends a feature exists.

---

## 5. Real test output (`cd hsf/deploy && node --test`)

Node `v22.22.3`. **No `npm install`; `node_modules` absent** — `stripe` and `@vercel/kv` are mocked at the module loader, so the suite runs dependency-free. Store used its in-memory fallback.

```
ok 1 - create-checkout-session returns 501 not_configured when no STRIPE_SECRET_KEY
ok 2 - create-checkout-session returns a checkout url when a key IS present (mocked Stripe)
ok 3 - webhook rejects a bad signature with 400
ok 4 - webhook returns 501 when unconfigured (no keys)
ok 5 - webhook writes an entitlement on a valid checkout.session.completed
ok 6 - entitlement route returns { paid:true } for a granted story
ok 7 - entitlement route returns { paid:false } for an unknown story
ok 8 - creators subscription: webhook grants by email, revoke on subscription.deleted
ok 9 - export STUB: 402 when unpaid, 501 not_implemented(stub) once entitled
ok 10 - END-TO-END loop: checkout -> webhook -> entitlement true (all mocked/in-memory)
# tests 10
# pass 10
# fail 0
```

This proves, per the task: (a) `create-checkout-session` returns `501` with no key and a session/link URL when a (mocked) key is present; (b) `webhook` rejects a bad signature (`400`) and, on a valid mocked `checkout.session.completed`, writes an entitlement via `store.js`; (c) the entitlement route then reads that entitlement `true`. Plus the creators subscribe/revoke path and the export gate.

Secret scan of `hsf/deploy/**` for `sk_live`/`sk_test_…`/`whsec_…`/`price_1…` (excluding `REPLACE_ME`/`MOCK`): **NO REAL SECRETS FOUND**. `.env.example` remains placeholders-only; no `.env` created.

---

## 6. What is NOT done — explicit gate statement

- **NO keys were set anywhere.** No real or test Stripe key/secret, no KV credentials. No `.env`. No network call to Stripe or KV was made.
- **Nothing was deployed.** No Vercel deploy, no daemon/launchagent touched, no money spent.
- **This is mocked, logic-level verification** — not a live or real Stripe-test-mode run.
- **FOUNDER-GATED (unchanged, per spec §5):** provisioning the live/real-test Stripe catalog, Vercel KV, setting env (`STRIPE_SECRET_KEY`, price IDs, `STRIPE_WEBHOOK_SECRET`, `AUTH_SECRET`, `BASE_URL`, KV vars), deploying, registering the live webhook, and making the first real purchase all remain founder-only. The `stripe_account_claimed` / price IDs in `product_registry.json` stay **UNVERIFIED** — this task did not confirm them.

Registry (`coordination/products/product_registry.json`) was **not modified**; `HSF_STORY_STUDIO` remains `3_PRODUCTIZED_DEFINED_ONLY` with `checkout_url: null`.
