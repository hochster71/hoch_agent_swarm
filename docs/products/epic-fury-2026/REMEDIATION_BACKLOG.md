# Remediation Backlog - Epic Fury 2026

* **Run ID**: 20260702T233000Z-epic-fury-2026-hasf-vetting

---

## 1. Backlog Items

### EF-REMED-01: Encapsulate RSS News Fetcher
* **Task**: Move RSS parsing helper `fetchAllNews` out of API route file and into `lib/news-fetcher.ts`.
* **Resolution**: Completed.

### EF-REMED-02: De-secret Push Env Scripts
* **Task**: Cleanse `push-supabase-env.sh` and `push-stripe-env.sh` by removing hardcoded credentials and loading dynamically from `.env.local` or user prompts.
* **Resolution**: Completed.

### EF-REMED-03: Dependency Vulnerability Upgrade
* **Task**: Run `npm audit fix` to clean indirect packages (`form-data` and `ws`).
* **Resolution**: Completed.

### EF-REMED-04: Implement Playwright E2E Tests
* **Task**: Author smoke, mobile, and accessibility test specs.
* **Resolution**: Completed.
