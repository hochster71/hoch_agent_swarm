# Epic Fury Pricing Model

This document outlines the subscription tiers and pricing strategies for Epic Fury.

## 1. Subscription Tiers

### Starter / Tier 1
- **Price**: $9.99 / month
- **Features**: Scoped local executions, basic node monitoring.
- **Target**: Individual hobbyists.

### Pro / Tier 2
- **Price**: $24.99 / month
- **Features**: Multi-node scheduling, 5 concurrent pods, advanced compliance maps.
- **Target**: High-performance builders.

### Enterprise / Tier 3
- **Price**: $79.99 / month
- **Features**: Uncapped local models, full zero-trust container routing, audit evidence ledger.
- **Target**: Security-critical enterprises.

## 2. Stripe Integration
- Subscriptions are managed via Stripe Checkout.
- Webhook endpoints map payments to local licenses.
- **Test Mode**: Enforced via `pk_test_` and `sk_test_` sandbox keys.
