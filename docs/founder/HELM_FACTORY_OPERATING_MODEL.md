# HELM Factory Operating Model

**Audience:** Michael (founder). **Purpose:** one operating model every HELM factory rides identically, from a produced artifact to a verified settled dollar — built so today's breakage class (expired key, empty envs, wrong-account price, a scaffold deploy clobbering a live app) stops recurring.

**Authored:** 2026-07-16. **Status of this doc:** the runtime is proven by soak; the go-to-market plumbing described here is being hardened *now* via the products manifest + guard-railed deploy pipeline + this doc. Where something is not yet proven, it says so. NO FAKE GREEN.

---

## The four decisions this model locks in

1. **ONE Stripe account is the merchant of record for ALL factories.** `acct_1Tdge9DINF9KNAIC` ("HOCH APPLICATION SOFTWARE FACTORY"). Every factory ships its *own* Stripe Product + Price(s) *inside that one account*; every checkout carries `metadata.factory=<HASF|HSF|HCF|…>` so revenue rolls up per factory from a single account, a single payout, a single tax/1099 entity, a single dashboard. **Do NOT create a Stripe account per factory.** Stripe Connect / separate accounts only when a factory becomes its own legal business.
2. **One repo → one Vercel project, strictly isolated.** A scaffold folder is NEVER cross-linked to a live project. `coordination/products/products.json` is the deploy source of truth; `scripts/factory_deploy.sh` enforces it. This exists because today a scaffold deploy clobbered a live app.
3. **One live key, one source, injected per project, rotated centrally.** No per-project manual paste. This exists because of the expired-key and empty-env incidents.
4. **A factory may only claim a rung it can PROVE.** Every rung on the Factory → Revenue Runway has an automated, no-fake-green check tied to the census and the runtime freshness service. Absence of evidence is a rung not reached.

---

## 1. Finance model — one account, many products

**Decision: one Stripe account, `acct_1Tdge9DINF9KNAIC`, is the single merchant of record for every factory.**

- Each factory ships its **own Stripe Product + one or more Prices** created *inside that one account*. Example (live-verified 2026-07-16): HSF's Story Studio prices `price_1TqjVNDINF9KNAICvsZ4Kl3t` ($19 one-time) and `price_1TqjVNDINF9KNAICsqE8sy0G` ($12/mo) both live in this account.
- **Every checkout is tagged `metadata.factory=<CODE>`** (HASF, HSF, HCF, HMF, HFF, …). That single tag is what makes per-factory revenue roll up out of one account — one payout, one tax/1099 entity, one dashboard, clean attribution.
- **Do NOT create a Stripe account per factory.** Per-account sprawl is exactly how the "wrong-account price" class of bug happens — a price minted in an account the live app doesn't checkout against. One account removes the entire failure mode.
- **Stripe Connect / a separate account is warranted only when a factory becomes its own legal business** (its own EIN, its own bank, its own liability). Until then: one account, tagged products.
- **Guardrail:** a price ID enters `products.json` only after it is retrieved from `acct_1Tdge9DINF9KNAIC` via the founder's authenticated Stripe CLI — never hand-typed, never trusted from a queue assertion. (The HSF prices above are marked live-verified precisely because they passed this retrieval check, not because someone claimed it.)

## 2. SDLC / deploy discipline — isolation or nothing

**Decision: one repo → one Vercel project, strict isolation, never cross-link a scaffold folder to a live project.**

Concrete lesson driving this: a **scaffold folder was deployed over a live app** — the exact accident this section forbids.

- `coordination/products/products.json` is the **deploy source of truth** for each product: its deploy source path, Stripe Product/Price IDs, the target Vercel project, and its health check. `scripts/factory_deploy.sh` reads that manifest and refuses to deploy a source path or project that the manifest does not sanction. (The manifest is the deploy half; `coordination/products/product_registry.json` is the monetization-ladder ledger the census scores. They are the two halves of one source of truth and are being unified — until then, both are authoritative for their half.)
- **Every deploy runs the same conveyor:** `preview → smoke-test → promote → auto-rollback on failure`.
  - *Preview:* deploy to a preview URL, never straight to production.
  - *Smoke-test:* health check must pass, and **for a sellable app the checkout endpoint must return a real Stripe session** (not a 501, not a stub) before promotion is allowed.
  - *Promote:* only a green preview is promoted to the live domain.
  - *Auto-rollback:* any failed post-promote check reverts to the last-good deploy automatically.
- **Isolation rule:** a scaffold (e.g. `hsf/deploy/`) is INERT by design and is bound to its own project. It is physically incapable of being promoted onto another product's live domain because the manifest maps each source to exactly one project, and `factory_deploy.sh` will not deploy a source→project pair the manifest doesn't declare.

## 3. Secrets management — one key, one source, central rotation

**Decision: one live key, one source, injected per project, rotated centrally — no per-project manual paste.**

Concrete lessons driving this: the **expired-key** incident (a live key aged out and nothing caught it) and the **empty-env** incident (a project deployed with unset envs and silently ran dead).

- **One canonical source** holds each live secret (live Stripe key, webhook secret, KV/store creds). Projects are *injected* from that source at deploy time; no human pastes a key into a project dashboard.
- **Rotation is central:** rotate once at the source, re-inject everywhere. No hunt-and-peck across N project dashboards.
- **Empty-env is a hard deploy failure:** `factory_deploy.sh` treats a required-but-unset env as a red gate — the deploy stops rather than shipping a dead app.
- **Founder-only boundary preserved:** Claude never types, stores, echoes, or hardcodes a secret. Where a live key or login is required, the script PAUSES at the native prompt (`stripe login`, `vercel login`, a one-time `sk_live_…` paste) and Michael enters it himself. That pause is the auth step, not a manual task list.

## 4. Factory → Revenue Runway — the conveyor every factory rides

The same rungs, in the same order, for every monetized factory. Each rung has an automated, no-fake-green check. A factory **cannot claim a rung it can't prove** — this is enforced by the census (`backend/mission_control/factory_census.py`) and kept honest/current by the runtime freshness service (`backend/runtime_freshness.py`).

| Rung | Means | Automated proof (no fake green) |
|------|-------|------------------------------|
| **PRODUCED** | A validated artifact exists (a governed mission ran and passed QA). | Census rungs RUNS→PRODUCES: a real dispatched mission + a validated artifact on disk. |
| **PRODUCTIZED** | That artifact has a **name and a price**. | Census reads the registry: no `price_usd` → not a product, stays DECLARED. |
| **DEPLOYED** | Live on an **isolated, health-checked** Vercel project. | `factory_deploy.sh`: preview health check green, promoted, rollback armed. |
| **SELLABLE** | A **real, reachable checkout** returns a live Stripe session. | Smoke-test hits the checkout endpoint and asserts a real `checkout.session` (not 501/stub). |
| **EARNING** | A stranger has **actually paid — settled**, evidenced revenue. | Balance transaction verified *settled* against the account, not asserted. Charge ≠ settled. |

**Live reads of this ladder today (honest):**
- **Epic Fury (HASF):** a real livemode charge of $20.52 exists; net $18.10 is held by Stripe **PENDING** until 2026-07-21. It sits at **SELLABLE** and auto-promotes to **EARNING** only when the balance transaction settles — verified against the account, never asserted early.
- **Story Studio (HSF):** app UI + buy-loop code are complete and pass 10/10 mocked tests; live prices are verified in the account. It is **PRODUCTIZED**, not sellable — the scaffold is inert (returns 501 with no keys) and $0 has settled. Remaining work is founder-gated: provision live keys + payout bank + KV, set env, deploy, register the live webhook, then one real settled purchase.
- **HFF Runway, HMF Cue Library:** **PRODUCTIZED (defined only)** — name + price, no checkout, $0. Defined ≠ produced ≠ sellable.
- **HHF, HPF:** non-monetized by design; exempt from the revenue ladder.

## 5. Honest readiness verdict

- **24/7 runtime: PROVEN.** The governed runtime has held under soak (minus the one gate we identified and fixed). This is the strong part of the system.
- **GTM plumbing: being hardened now.** The single-account finance model, the `products.json` manifest, the guard-railed `factory_deploy.sh` pipeline, and this doc are the hardening. Two of those (manifest, pipeline) are in flight as this is written — treat them as landing, not landed, until their own checks are green.
- **Always founder-only, by design and permanently:** moving money, holding/flipping live keys, publishing to a store, and approving an irreversible deploy. Claude scripts everything up to that last click and yields; Michael performs the biometric/passkey auth and the final approve. That boundary is not a gap to close — it is the design.

**Bottom line:** the machine that *runs* factories is proven; the machine that *sells* their output is being made as disciplined as the runtime. When both are green, any factory that produces a validated artifact rides one identical conveyor to a settled dollar — and can never again claim a rung it hasn't proven.

---

*File: `docs/founder/HELM_FACTORY_OPERATING_MODEL.md`. Related instruments: `coordination/products/products.json` (deploy manifest), `coordination/products/product_registry.json` (monetization ledger), `scripts/factory_deploy.sh` (pipeline), `backend/mission_control/factory_census.py` (rung scoring), `backend/runtime_freshness.py` (freshness).*
