# Story Studio — Stripe "No such price" mismatch: root-cause (read-only)

- **When:** 2026-07-16
- **Symptom:** live checkout at `story-studio-live.vercel.app` returns
  `No such price: 'price_1TqjVNDINF9KNAICvsZ4Kl3t'` after a new live
  `STRIPE_SECRET_KEY` was set in Vercel.
- **Method:** read-only. Stripe MCP (`fetch_stripe_resources`,
  `get_stripe_account_info`) + Vercel MCP + repo cross-reference. Nothing was
  changed; no Stripe object created.

## Evidence

**1. Two distinct live Stripe accounts are in play. Stripe object IDs are
account-scoped — the suffix after the timestamp encodes the owning account:**

| Account | Display name | Object-ID suffix | Verified how |
|---|---|---|---|
| `acct_1TPOYkDK7Brrgheo` | **Epic Fury** | `...DK7Brrgheo` | `get_stripe_account_info` — this is the account the connected Stripe MCP/CLI-key is authenticated as |
| `acct_1Tdge9DINF9KNAIC` | **HOCH APPLICATION SOFTWARE FACTORY** | `...DINF9KNAIC` | founder's other authenticated key retrieves `price_1TqjVN...` here (task evidence + `hsf/deploy/go_live.sh`) |

**2. The Story Studio price IDs belong to `acct_1Tdge9DINF9KNAIC`
(suffix `DINF9KNAIC`), NOT to the account the connected key is on.** Retrieving
them through the connected Stripe MCP (which is `acct_1TPOYkDK7Brrgheo` / Epic
Fury) reproduces the exact production error:

```
fetch_stripe_resources price_1TqjVNDINF9KNAICvsZ4Kl3t
  -> Invalid API request to Stripe API: No such price: 'price_1TqjVNDINF9KNAICvsZ4Kl3t'
fetch_stripe_resources price_1TqjVNDINF9KNAICsqE8sy0G
  -> Invalid API request to Stripe API: No such price: 'price_1TqjVNDINF9KNAICsqE8sy0G'
```

**3. Control — a price that DOES live on the connected account resolves fine:**

```
fetch_stripe_resources price_1TsnrvDK7BrrgheoqJxC3QxU   (Epic Fury $19)
  -> { unit_amount: 1900, currency: usd, product: prod_UsYzlrB2MYctkg }   OK
```

**4. The app reads its price IDs from env, not hardcode:**
`hsf/deploy/pricing.config.json` maps tiers to `STRIPE_PRICE_ONESTORY` /
`STRIPE_PRICE_CREATORS`, consumed by `api/create-checkout-session.js`. So the
price IDs and the secret key are set independently in Vercel and can drift onto
different accounts.

## Findings (answers the three questions)

**(a) Which account owns `price_1TqjVNDINF9KNAICvsZ4Kl3t`?**
`acct_1Tdge9DINF9KNAIC` — "HOCH APPLICATION SOFTWARE FACTORY". Proven by the ID
suffix (`DINF9KNAIC`) and by the founder's own key retrieving it successfully.
The price is **NOT deleted** — it exists and is retrievable under its own
account. (The connected MCP is a *different* account, so it cannot see it.)

**(b) Do the app-config price IDs belong to the same account as the new key?**
**No.** The price IDs (`price_1TqjVN...DINF9KNAIC`) belong to
`acct_1Tdge9DINF9KNAIC`. The newly-set live key is from a *different* account —
that is the whole reason the price is invisible to it. (A live key from
`acct_1Tdge9DINF9KNAIC` would resolve its own price; the error proves the key is
not from that account.)

**(c) Most likely cause of "No such price":**
**Price/key account mismatch** — the live `STRIPE_SECRET_KEY` now set in Vercel
is from a different Stripe account than the one that owns the price IDs. It is
NOT a deletion (price still exists) and NOT primarily a test-vs-live confusion
(the price exists in *live* on its account). Given only two live accounts are in
play, the newly-set key is almost certainly the **Epic Fury account
(`acct_1TPOYkDK7Brrgheo`)** key — the same account whose API independently
returns the identical "No such price" for these IDs above. (Residual to confirm
at the dashboard: rule out a test-mode key of the HOCH account.)

## Fix direction (NOT applied — founder-gated)

Make the key and the price IDs agree on ONE account. Either:
- set `STRIPE_SECRET_KEY` in the `story-studio-live` Vercel project to a **live
  key from `acct_1Tdge9DINF9KNAIC`** (the account that owns the current price
  IDs); **or**
- recreate the $19/$12 prices in whatever account the new key belongs to and
  update `STRIPE_PRICE_ONESTORY` / `STRIPE_PRICE_CREATORS` to the new IDs.

Verify with: `POST /api/create-checkout-session {"product":"onestory"}` returns
a `checkout.stripe.com/...` URL instead of "No such price".

## Related clobber risk (surfaced during this investigation)

The live app served at `story-studio-live.vercel.app` (title "Story Studio —
your life, as a cinematic storybook", loads `engine.js`, posts `/api/save-story`)
**exists nowhere in this repo** — not in the working tree and not in git at the
deployed SHA `3ed760e2` (branch `helm/h1b-r2-remediation`). The production deploy
carried `gitDirty: 1`, i.e. it was built from uncommitted local files. `hsf/deploy`
is the INERT scaffold with a *different* UI and is **not** the live source.
Do NOT redeploy from `hsf/deploy` or a clean checkout — it would clobber the live
app. Recover the live source from the Vercel project (existing production build /
rollback candidate) and commit it before touching the key/price env.
