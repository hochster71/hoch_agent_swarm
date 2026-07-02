# HASF Founder Review Package

* **Author**: HELM
* **Status**: `READY_FOR_FOUNDER_REVIEW`

---

## 1. What is being sold?
A continuous, high-frequency **Agentic Security & QA Audit Package** tailored for startup repositories. It integrates automated security gates, dependency scanning, code sanity audits, and visual telemetry dashboards.

## 2. Who are the first 10 targets?
1. Startup Alpha (AI developer platform)
2. Beta Labs (relational database tooling)
3. Delta SaaS (medical billing APIs)
4. Gamma Systems (IoT telemetry integration)
5. Epsilon Engineering (logistics automation)
6. Zeta Devs (digital design systems agency)
7. Eta Finance (open-banking APIs)
8. Theta Analytics (marketing data streams)
9. Iota Infrastructure (cloud container management)
10. Kappa Kernels (edge firmware consulting)

## 3. What is the price?
* **Starter Tier**: $49/month (daily static checks, single repository)
* **Growth Tier**: $149/month (hourly static + dependency checks, up to 3 repositories)
* **Enterprise Tier**: $499/month (custom logic gates, E2E test suite integration, unlimited repositories)

## 4. What does the buyer receive?
* Access to a custom control plane UI displaying live pass/fail gate metrics.
* Automatic alerts for code base path contamination and dependency vulnerabilities.
* Hashed and verified evidence logs packaged into a tamper-proof manifest.

## 5. How is it delivered?
Automated runs execute containerized tests and compile verification statuses. The results are instantly synced to the client's dashboard interface.

## 6. What is the Stripe-safe payment path?
* The billing flow uses standard Stripe Checkout in `test-mode` (sandbox).
* **Bank Details Stored**: `false` (payout accounts and routing parameters are never persisted locally)
* **Stripe Live Charging**: Disabled (locked to sandbox tokens until manual activation)

## 7. What must Michael approve before live charging?
Michael must sign off on:
1. Validating payout bank routing parameters.
2. Formally setting the `HASF_STRIPE_PRODUCTION_MODE` flag to `true` in environment configuration.
