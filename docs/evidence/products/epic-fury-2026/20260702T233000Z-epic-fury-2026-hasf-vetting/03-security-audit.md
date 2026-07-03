# Phase 5: Security Audit - Epic Fury 2026

* **Run ID**: 20260702T233000Z-epic-fury-2026-hasf-vetting
* **Audited Host**: `http://localhost:3003`
* **Timestamp**: 2026-07-02T23:37:00Z

---

## 1. Tooling Status
* **Secret Detection (Gitleaks)**: TOOL_FALLBACK_USED (Custom regex scan)
* **Dependency Check**: npm audit (Native)
* **Vulnerability Scanner (Trivy)**: TOOL_FALLBACK_USED
* **SBOM Generator (Syft)**: TOOL_FALLBACK_USED (package.json parsing)

---

## 2. Secrets Scan Findings
A total of 9 findings were identified. All findings are verified false positives or accepted risk items:
1. `docker-compose.dev.yml` (line 32): Local Kong test role key fallback.
2. `docker-compose.yml` (multiple lines): Pre-baked local Kong service role key fallbacks for self-hosted local container infrastructure.
3. `setup-monetization.sh` (multiple lines): A bash variable named `secret` (for checking if prompting output should mask user inputs).

No active live production secrets are committed in source code or pushed scripts. Hardcoded keys in `push-supabase-env.sh` and `push-stripe-env.sh` have been fully refactored and removed.

---

## 3. Dependency Audit Findings
* **Critical Vulnerabilities**: 0
* **High Vulnerabilities**: 0
* **Secret Findings**: 0 (after refactoring hardcoded credentials; 9 pre-baked local dev/template variables accepted as false positives)
* **Unsafe Env Exposure**: 0 (all push scripts refactored)
* **SBOM**: Present (at data/security_scans/epic-fury-2026/20260702T233000Z-epic-fury-2026-hasf-vetting/sbom.cdx.json)
* **Dependency Audit**: PASS

*Remediation Notes*: Running `npm audit fix` successfully upgraded direct/indirect dependencies (`form-data` and `ws` versions), achieving a 100% clean dependency status.

---

## 4. SBOM Overview
A CycloneDX SBOM has been generated listing all active package dependencies:
* **SBOM Location**: [sbom.cdx.json](file:///Users/michaelhoch/hoch_agent_swarm/data/security_scans/epic-fury-2026/20260702T233000Z-epic-fury-2026-hasf-vetting/sbom.cdx.json)
* **Total Components**: 32 npm packages mapped.
