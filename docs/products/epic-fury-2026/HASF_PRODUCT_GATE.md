# HASF Product Gate: Epic Fury 2026

* **Pipeline Owner**: HASF Vetting Team
* **Target Product**: Epic Fury 2026

---

## 1. Product Gate Definitions

| Gate | Status | Required Checks |
|---|---|---|
| **epic_fury_repo_access_gate.sh** | `PENDING` | Local folder access, git branch validation, files inventory check. |
| **epic_fury_product_definition_gate.sh** | `PENDING` | Product brief, founder intent, and ship criteria existence. |
| **epic_fury_build_test_gate.sh** | `PENDING` | npm installation, Next build, typescript checks, and test runner outputs. |
| **epic_fury_ui_ux_gate.sh** | `PENDING` | Smoke, mobile layout, and console error checks. |
| **epic_fury_security_gate.sh** | `PENDING` | Gitleaks, dependency audits, and license check sweeps. |
| **epic_fury_gap_gate.sh** | `PENDING` | Resolution of all high-priority gaps. |
| **epic_fury_shipping_gate.sh** | `PENDING` | Full release package compilation and founder verification checks. |
