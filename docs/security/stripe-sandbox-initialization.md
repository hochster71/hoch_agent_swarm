# Stripe Sandbox / Test-Mode Initialization Policy

This document outlines the zero-trust security requirements for managing Stripe API keys in the HOCH PODS and HAS/HASF environments.

## 1. Secrets Committal Prevention (Zero Trust)
No production or live Stripe credentials (`pk_live_`, `sk_live_`, `whsec_` for live webhooks) may ever be committed to git, written to public repositories, or stored in plaintext configuration files. 

## 2. Stripe Test-Mode Environment Variables
For sandbox and E2E verification, only test-mode keys starting with the appropriate test prefix may be loaded into the runtime.
- **Publishable Key**: Must start with `pk_test_`
- **Secret Key**: Must start with `sk_test_`
- **Webhook Secret**: Must start with `whsec_`

## 3. Configuration Template (.env.example)
A safe template of environment variables containing placeholders only is maintained in [.env.example](file:///Users/michaelhoch/hoch_agent_swarm/.env.example). 

## 4. Fail-Closed Production Default
In the absence of explicitly configured production keys in the server environment, the payment gates must fail-closed. No premium feature access is granted and no stripe connection is assumed active.
