# Vercel Bypass Token Remediation - Epic Fury 2026

* **Run ID**: `20260702T233000Z-epic-fury-2026-hasf-vetting`
* **Candidate Commit**: `3e94f322dc1373358935dd303c0269b36a0ee5ba`
* **Timestamp**: 2026-07-03T02:13:00Z

---

## 1. Finding
During staging asset loading verification, the Vercel deployment protection bypass token was inadvertently exposed/printed in plain text in the report, log, and spec files.
* **Severity**: `HIGH` (Allows bypassing the preview environment SSO protection).

---

## 2. Remediation Steps & Verification

### Action: Bypass Token Rotated/Disabled
* Disabled the exposed bypass secret via Vercel CLI:
  `npx vercel project protection disable --protection-bypass --protection-bypass-secret dlA54TQb...`
* Rotated the Vercel Automation Bypass token to a new secret value on the Vercel team project dashboard.
* Verified that requests carrying the old bypass header are rejected by Vercel interceptors, returning an HTTP `302 Redirect` to Vercel SSO login.

### Codebase & Evidence Sanitization
* **Repo Scan**: `PASS` (Global grep searches for the exposed secret pattern returned zero matches across the entire codebase).
* **Evidence Scan**: `PASS` (All markdown files, test spec files, and runner scripts have been sanitized to dynamically fetch the bypass token from Vercel's config API at runtime).

---

## 3. Posture Verification Gates
* **Security Gate**: `PASS`
* **Shipping Gate**: `PASS`
* **Live Release Status**: `live_release_authorized = false`
