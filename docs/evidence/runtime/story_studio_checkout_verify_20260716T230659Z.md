# Story Studio LIVE checkout verification — BOTH tiers

**Captured (UTC):** 2026-07-16T23:06:59Z
**Endpoint:** `POST https://story-studio-live.vercel.app/api/create-checkout-session`
**Doctrine:** NO FAKE GREEN — this proves the checkout returns a real Stripe URL (rung 4 SELLABLE). It does NOT prove any dollar has settled; `revenue_settled_usd` stays 0.0 until Stripe's balance transaction confirms.

## Method
```
curl -s -X POST https://story-studio-live.vercel.app/api/create-checkout-session \
  -H 'Content-Type: application/json' -d '{"tier":"onestory"}'
curl -s -X POST https://story-studio-live.vercel.app/api/create-checkout-session \
  -H 'Content-Type: application/json' -d '{"tier":"creators"}'
```

## Raw responses

### Tier: onestory ($19 one-time)
```json
{"url":"https://buy.stripe.com/5kQ28rf2aeS36sq57I5J602"}
```
Stripe URL returned: **https://buy.stripe.com/5kQ28rf2aeS36sq57I5J602** — real `buy.stripe.com` link. PASS.

### Tier: creators ($12/mo)
```json
{"url":"https://buy.stripe.com/3cIdR9g6e7pB4ki8jU5J603"}
```
Stripe URL returned: **https://buy.stripe.com/3cIdR9g6e7pB4ki8jU5J603** — real `buy.stripe.com` link. PASS.

## Verdict

| Tier | Price | Response | Stripe URL | Verdict |
|---|---|---|---|---|
| onestory | $19 one-time | `{"url":"https://buy.stripe.com/5kQ28rf2aeS36sq57I5J602"}` | buy.stripe.com/5kQ28rf2aeS36sq57I5J602 | LIVE / buyable |
| creators | $12/mo | `{"url":"https://buy.stripe.com/3cIdR9g6e7pB4ki8jU5J603"}` | buy.stripe.com/3cIdR9g6e7pB4ki8jU5J603 | LIVE / buyable |

**BOTH tiers return a real Stripe checkout URL.** Story Studio's live checkout is genuinely buyable on evidence → rung 4_SELLABLE.

**Not claimed:** no settled dollar. Rung 5_EARNING requires a real charge whose Stripe balance transaction reaches `available`. Until then revenue_settled_usd = 0.0.
