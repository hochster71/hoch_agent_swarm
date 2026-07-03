# Ship Criteria: Epic Fury 2026

* **Product ID**: Product 001
* **Vetting Pipeline**: HASF Shipping Pipeline

---

## 1. Quality & Performance Thresholds
* **Build status**: `SUCCESS` (`next build` must execute without error or warnings)
* **TypeScript compile**: `SUCCESS` (`tsc --noEmit` must pass cleanly)
* **Linting**: `SUCCESS` (No errors or warning in `next lint`)
* **Unit tests**: `PASS` (All contract and smoke tests must return success)

## 2. Security Thresholds
* **Secrets check**: `PASS` (No unencrypted keys, tokens, or credentials in codebase)
* **Vulnerabilities**: `PASS` (Zero unaccepted critical or high vulnerabilities)
* **OAuth controls**: `PASS` (Google OAuth toggle active, magic link default)

## 3. UI/UX & Accessibility Thresholds
* **Dashboard rendering**: `PASS` (Scanline overlay, Sidebar, TopBar, and feed components render correctly)
* **Console hygiene**: `PASS` (Zero console errors during homepage loads)
* **Mobile responsiveness**: `PASS` (Sidebar collapses appropriately on mobile viewports)

## 4. Release Authorization
* **Founder Signoff**: Required (release is blocked until explicit confirmation is obtained)
* **Final Verifier Verdict**: Required
