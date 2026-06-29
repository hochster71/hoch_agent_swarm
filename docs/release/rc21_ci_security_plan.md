# Release CI Security Plan (rc21)

This document establishes the automation, CI scanning gates, SBOM generation, and release provenance details for the `rc21` release. The target is to transition the `rc20` "GO WITH OPERATIONAL WARNING" release posture into a clean "GO" by enforcing security validation in GitHub Actions.

---

## 1. Baseline Coordinates
- **Baseline Commit:** `c72b6254bd62065ea3ea45bab0123e090bc3df82`
- **Baseline Tag:** `rc20-integrated-hardening`
- **Baseline Posture:** GO WITH OPERATIONAL WARNING (due to missing Semgrep/Trivy binaries on developer host).

---

## 2. rc21 Security Objectives
- **Objective:** Automate security gates in CI/CD pipeline, making security validation mandatory for merging to `master` and release tagging.
- **Goal:** Shift the operational security review from a manual checklist to an automated, fail-closed CI gate.

---

## 3. GitHub Actions CI Configuration
The GitHub Actions workflow is defined in `.github/workflows/rc21-security.yml` and executes on:
- All pull requests.
- Pushes to `master` and `rc21-ci-enforced-security` branches.
- Manual triggers via `workflow_dispatch`.

### Automated Gates & Fail Thresholds
1. **`test` (Unit Tests):** Checks python code functionality via `uv run pytest -q`. Fails on any test failure.
2. **`semgrep` (Static Application Security Testing):** Runs custom SAST checks defined in `qa/semgrep/hoch-security.yml`. Fails on any finding unless marked `INFO`.
3. **`trivy-fs` (Vulnerability Scanning):** Scans the project filesystem for known package and config vulnerabilities. Fails if any `CRITICAL` issues are found.
4. **`docker-build-and-trivy-image` (Image Vulnerability Scanning):** Builds the application container and scans the image layers. Fails on any `CRITICAL` image vulnerability.
5. **`compose-validate` (Infrastructure Configuration):** Assures compose file parsing matches the modern specification (fails if obsolete top-level `version` properties are found).
6. **`provenance-summary` (Release Summary):** Auto-generates a detailed GHA Run Summary listing files, test outcomes, commit coordinates, and digests.

---

## 4. SBOM Generation
- **Method:** Dynamically utilizes `cyclonedx-py` (via Astral `uvx` runner to avoid permanent package pollution).
- **Target path:** `artifacts/security/sbom-rc21.json`
- **Format:** CycloneDX 1.5 JSON containing the complete Python dependency tree.

---

## 5. Local Workstation Commands & Execution
Developers can test their security posture locally prior to committing changes:

### Run Security Gate Checks
```bash
./scripts/security/rc21_security_gate.sh
```
*Note:* If optional scanner binaries (`semgrep`, `trivy`) are missing locally, the script outputs warnings and installation steps but exits with code `0` (assuming unit tests and compose checks pass) to defer heavy scanner enforcement to the CI run.

### Generate Dependency SBOM
```bash
./scripts/security/generate_sbom.sh
```

---

## 6. Workstation Limitations
- Developer workstations that lack native `semgrep` or `trivy` installations will show warnings during local execution. Full scanning checks are guaranteed by the GitHub Actions runners which run inside clean, controlled environments where all required dependencies are available.
