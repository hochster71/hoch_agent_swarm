# CyberQRG — `--plan` mode result (read-only verification)

**Product id:** `HCF_CYBERQRG_AI` (Hoch Cyber Factory)
**Command run:** `bash scripts/factory_to_money.sh HCF_CYBERQRG_AI --plan`
**Mode:** PLAN — read-only. Pasted nothing, created no Stripe objects, set no env, deployed nothing.
**Verified:** 2026-07-16 (against the real repo files; PLAN makes no network calls — the Stripe/Vercel calls are `--go`-only).

---

## VERDICT

**Almost one `--go` from live — but NOT a clean single command yet.** The two things that must resolve for a safe deploy *do* resolve; one fixable manifest gap and the (by-design) founder Stripe paste remain.

### What PLAN confirmed GREEN

- **Source-match guard resolves and PASSES.** `source_of_truth` = `products/cyberqrg-ai/deploy`, which resolves to a real directory *inside the repo*. The guard prints `[PASS] source resolves inside the repo`. The real deploy bundle is present and verified on disk: `public/index.html`, `public/success.html`, `api/create-checkout-session.js`, `vercel.json`, `package.json`, `.env.example`. This is the anti-clobber gate — it is satisfied.
- **Product / tier / price plan resolves.** Exactly **1 sellable tier**: `scanpack`, `$9`, `one_time` → env var `STRIPE_PRICE_SCANPACK`. Idempotency strategy is well-formed: Stripe product reused/created by `metadata.helm_product_id=HCF_CYBERQRG_AI`; price reused/created by stable `lookup_key=helm_hcf_cyberqrg_ai_scanpack`. No duplicate-on-rerun risk.
- **Guarded deploy layer present.** `scripts/factory_deploy.sh` is present + executable; the deploy would ride preview → smoke → promote → auto-rollback (never a raw `vercel deploy --prod`).
- **PLAN exited 0** and stopped cleanly at "nothing was paid, set, or deployed."

### The one FIXABLE MANIFEST GAP (precise; do NOT invent an id)

**The Vercel project target is a placeholder, and the guarded deploy layer would abort on it.**

- In `coordination/products/products.json`, the `HCF_CYBERQRG_AI` record has **no `vercel_project` field**. It only has `vercel_project_id` and `vercel_project_name`, and **both are the literal string `"UNKNOWN"`**.
- `scripts/factory_deploy.sh` reads the field **`.vercel_project`** (line 111, `VERCEL_PROJECT="$(jqget '.vercel_project')"`) with **no fallback**, and at line 118 does:
  `[ -n "$VERCEL_PROJECT" ] || die "manifest record for '$PRODUCT_ID' is missing vercel_project."`
- Therefore, at `--go`, after Stripe prices are created and Vercel env is set, `factory_to_money.sh` hands off to `factory_deploy.sh`, which would **`die` on the missing `vercel_project`** before any deploy happens.
- The manifest itself flags a *candidate* — `beyond-tomorrow-cyber-mvp` (`prj_h959G6w2eowieCxHgL5viESH4hAv`, team `hasf`) — but explicitly marks it **NOT confirmed linked** to this product. **No real project id is invented here** (doctrine + NO FAKE GREEN). It must be created or confirmed by the founder.

### The (by-design) founder gate

- `stripe_account_id` = `UNKNOWN (none wired yet)`. This is intentional. At `--go` the script opens a **hidden native prompt** for a one-time paste of the `sk_live_…` key, validates it directly against `api.stripe.com` (`GET /v1/account`), then creates the $9 price in *that key's own account*. Claude never sees the key.
- The Keychain item `helm-stripe-hcf_cyberqrg_ai` does not exist yet (expected on first run). (In this Linux verification sandbox the macOS `security` CLI is absent, so PLAN reported it missing — on Michael's Mac this is simply the "will prompt once" path.)
- `live_url` = `UNKNOWN` until the first deploy assigns it.

---

## THE EXACT REMAINING FOUNDER STEP

1. **Create or confirm the CyberQRG Vercel project**, then record its real name in the manifest.
   - Either confirm the candidate `beyond-tomorrow-cyber-mvp` is the intended project, **or** create a fresh dedicated project (e.g. `cyberqrg-ai`) under team `hasf`.
   - Edit the `HCF_CYBERQRG_AI` record in `coordination/products/products.json` so it has a real **`vercel_project`** field (the project *name* factory_deploy reads), and fill in `vercel_project_id` / `vercel_project_name` with the real values. Do not guess — use the confirmed project.

2. **Run one `--go` from the verified source dir:**
   ```
   cd /Users/michaelhoch/hoch_agent_swarm/products/cyberqrg-ai/deploy
   /Users/michaelhoch/hoch_agent_swarm/scripts/factory_to_money.sh HCF_CYBERQRG_AI --go
   ```
   This single command will, in order: prompt once (hidden) for the `sk_live_…` paste → validate it against api.stripe.com → idempotently create the `$9` `scanpack` product+price in that account → set `STRIPE_SECRET_KEY` + `STRIPE_PRICE_SCANPACK` in Vercel prod env → hand off to `factory_deploy.sh` for preview → checkout smoke-test → promote → auto-rollback on failure.
   Requires the founder to be signed into Vercel (`vercel whoami` must succeed).

**Bottom line:** the code, the checkout, and the source-guard are ready. Step 1 (record a real Vercel project in the manifest) is the one gap that must close *before* `--go` will complete; step 2 is the founder's single armed command with his Stripe paste. No live action was taken.
