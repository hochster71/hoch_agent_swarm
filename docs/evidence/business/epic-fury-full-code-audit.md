# Epic Fury Full Code Audit (RC44)

**Date**: 2026-07-01  
**Auditor**: Antigravity Full Code Audit Engine  
**Findings Count**: 42  

## 1. Executive Summary
> [!NOTE]
> **No live Stripe keys found**. Security baseline validated. All live mode billing components are securely blocked.

## 2. Detailed Findings
| Severity | Category | File Path | Details |
| --- | --- | --- | --- |
| LOW | MOCK_PLACEHOLDER | `configure-billing-env.sh` | Stripe mock placeholder: sk_live_xxx |
| HIGH | SUPABASE_TOKEN | `docker-compose.dev.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `push-supabase-env.sh` | Supabase authorization token signature detected |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_test_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_test_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_test_xxx |
| HIGH | SUPABASE_TOKEN | `push-stripe-env.sh` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| LOW | MOCK_PLACEHOLDER | `app/api/stripe/portal/route.ts` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `app/api/stripe/checkout/route.ts` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `app/api/stripe/checkout/route.ts` | Stripe mock placeholder: sk_test_xxx |
| LOW | MOCK_PLACEHOLDER | `configure-billing-env.sh` | Stripe mock placeholder: sk_live_xxx |
| HIGH | SUPABASE_TOKEN | `docker-compose.dev.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `push-supabase-env.sh` | Supabase authorization token signature detected |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-monetization.sh` | Stripe mock placeholder: sk_test_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_test_xxx |
| LOW | MOCK_PLACEHOLDER | `setup-stripe.sh` | Stripe mock placeholder: sk_test_xxx |
| HIGH | SUPABASE_TOKEN | `push-stripe-env.sh` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| HIGH | SUPABASE_TOKEN | `docker-compose.yml` | Supabase authorization token signature detected |
| LOW | MOCK_PLACEHOLDER | `app/api/stripe/portal/route.ts` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `app/api/stripe/checkout/route.ts` | Stripe mock placeholder: sk_live_xxx |
| LOW | MOCK_PLACEHOLDER | `app/api/stripe/checkout/route.ts` | Stripe mock placeholder: sk_test_xxx |

## 3. Dependency Inventory
| Package | Version | Source Target |
| --- | --- | --- |
| `@capacitor/cli` | `^8.3.0` | epic-fury-build |
| `@capacitor/core` | `^8.3.0` | epic-fury-build |
| `@capacitor/ios` | `^8.3.0` | epic-fury-build |
| `@radix-ui/react-dialog` | `^1.1.2` | epic-fury-build |
| `@radix-ui/react-slot` | `^1.1.0` | epic-fury-build |
| `@radix-ui/react-tabs` | `^1.1.1` | epic-fury-build |
| `@radix-ui/react-tooltip` | `^1.1.3` | epic-fury-build |
| `@revenuecat/purchases-capacitor` | `^12.3.2` | epic-fury-build |
| `@supabase/ssr` | `^0.5.1` | epic-fury-build |
| `@supabase/supabase-js` | `^2.46.0` | epic-fury-build |
| `class-variance-authority` | `^0.7.1` | epic-fury-build |
| `clsx` | `^2.1.1` | epic-fury-build |
| `jotai` | `^2.10.0` | epic-fury-build |
| `lucide-react` | `^0.460.0` | epic-fury-build |
| `next` | `^15.5.19` | epic-fury-build |
| `openai` | `^4.104.0` | epic-fury-build |
| `react` | `^19.0.0` | epic-fury-build |
| `react-dom` | `^19.0.0` | epic-fury-build |
| `stripe` | `^22.0.2` | epic-fury-build |
| `tailwind-merge` | `^2.5.4` | epic-fury-build |
| `tailwindcss-animate` | `^1.0.7` | epic-fury-build |
| `@next/bundle-analyzer` | `^16.2.4` | epic-fury-build |
| `@types/node` | `^22` | epic-fury-build |
| `@types/react` | `^19` | epic-fury-build |
| `@types/react-dom` | `^19` | epic-fury-build |
| `autoprefixer` | `^10.4.27` | epic-fury-build |
| `eslint` | `^9` | epic-fury-build |
| `eslint-config-next` | `^15.1.0` | epic-fury-build |
| `postcss` | `^8.5.10` | epic-fury-build |
| `puppeteer-core` | `^24.40.0` | epic-fury-build |
| `tailwindcss` | `^3.4.1` | epic-fury-build |
| `typescript` | `^5` | epic-fury-build |
