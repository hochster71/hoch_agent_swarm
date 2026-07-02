# HASF Stripe Safe Revenue Boundary

* **Status**: `ACTIVE_BOUNDARY_ENFORCED`
* **Stripe Payment Path Status**: `TEST_MODE_READY`
* **Bank Details Stored**: `false`
* **Stripe Live Charging Enabled**: `false` (LOCKED pending explicit founder signature)

---

## Safety Controls
1. No banking credentials or payout routing numbers may be stored in code, logs, environment configurations, or git history.
2. The Stripe SDK must default to sandbox modes until a formal manual signoff overrides the environment variable `HASF_STRIPE_PRODUCTION_MODE` to `true`.
3. All production charge intents must go through an out-of-band founder review hook.
