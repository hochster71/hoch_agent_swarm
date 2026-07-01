# Runbook: Stripe Sandbox Readiness Check (RC40)

This runbook documents how to run, verify, and maintain the Stripe Sandbox Readiness checks in the HAS/HASF environment.

## 1. Sandbox Environment Secrets Configuration
- **File Name**: `.env.stripe.sandbox`
- **Location**: Project root (`/Users/michaelhoch/hoch_agent_swarm/`)
- **Properties**:
  - `STRIPE_MODE`: Must be exactly `sandbox`
  - `STRIPE_ACCOUNT_EMAIL`: Stripe user account identifier email
  - `STRIPE_PUBLISHABLE_KEY`: Must start with `pk_test_`
  - `STRIPE_SECRET_KEY`: Must start with `sk_test_` or `rk_test_`
- **Permissions**: File permissions must be set to `600` (readable/writable by owner only).

## 2. Key Invariant Audits
- **Live Key Blocking**: Any key starting with `pk_live_`, `sk_live_`, or `rk_live_` is strictly blocked and classifies the setup as `INVALID`.
- **Git Safety**: `.env.stripe.sandbox` is ignored in `.gitignore` to prevent accidental commits to remote repositories.
- **Privacy Policy**: Plaintext secrets are never logged, printed, or returned via APIs. Only the schema presence status (`PRESENT`, `MISSING`, `INVALID`) is returned.

## 3. Cockpit API Verification
- The dashboard queries `GET /api/pert/data` which returns:
  - `"stripe_sandbox_readiness"`: Sourced from `stripe_policy_check` containing `PRESENT`, `MISSING`, or `INVALID`.
  - `"monetization_readiness_percent"`: Capped at 50% if sandbox state is `MISSING` or `INVALID`. Uncapped (100% when evidence logs are all present) if the state is `PRESENT`.
