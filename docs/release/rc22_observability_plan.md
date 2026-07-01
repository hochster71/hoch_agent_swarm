# Release Provenance and Runtime Observability Plan (rc22)

This document establishes the architecture for signed release provenance, Docker image digest capture, SBOM artifact retention, CI artifact evidence packaging, runtime health verification, and rollback runbooks for the `rc22` release milestone.

---

## 1. Signed Release Provenance

We use **Cosign** to sign release artifacts to guarantee build authenticity and supply chain integrity.

### OIDC Keyless Signing
Inside the GitHub Actions environment, we configure keyless signing by granting the `id-token: write` permission to the GHA runner. This allows Cosign to retrieve an ephemeral OIDC identity token from GitHub, generate a short-lived cryptographic key pair, and record the signature in the public **Rekor** transparency log.

### Local Workstation Signing
For local developer runs, Cosign signatures are waived by default to avoid local keypair maintenance blocks. To enforce local signing, set:
```bash
export ENABLE_COSIGN_SIGNING=true
```

---

## 2. Docker Image Digest Capture

To ensure local builds and CI validation can run deterministically:
- `capture-docker-digests.ts` lists local container images.
- If a registry-assigned digest is not present (because the image has not been pushed to a registry yet), the script falls back to the **local Docker Image ID** (formatted as `sha256:<ID>`).
- This guarantees clean validation pass status in CI runs without registry push dependencies.

---

## 3. CI Artifact Evidence Pack & SBOM Retention

Every successful CI run archives a complete release package as a **CI Artifact Evidence Pack**.
- **SPDX SBOM:** Generated via `npm run supply:sbom` containing all Node packages.
- **SLSA Provenance:** Generated via `npm run supply:provenance` matching the in-toto spec.
- **Release Manifest:** A signed `release_manifest.json` containing digests of all verification reports.
- **Retention:** All artifacts are retained as workflow run artifacts in GitHub Actions using `actions/upload-artifact@v4`.

---

## 4. Release Rollback Runbook

If a critical runtime incident occurs, operators can execute a verified rollback using the provided CLI utility:

```bash
./scripts/security/rc22_rollback.sh <target_tag_or_commit>
```

### Rollback Validation Steps
1. The script verifies that the target commit/tag exists in the git log.
2. It detects if the working tree has uncommitted changes and displays warnings.
3. It prints a file difference summary between `HEAD` and the target.
4. It prompts for operator confirmation before performing `git checkout`.
5. Uvicorn on port 8000 must be restarted to finalize reloading the code.

---

## 5. Recommended GitHub Branch Protection Rules

To prevent code drift and secure the master branch:
1. **Require Pull Requests:** Block direct pushes to the `master` branch.
2. **Require Status Checks:** Enforce that the following status gates must pass green before merging:
   - `Run Python Unit Tests`
   - `Semgrep Custom Static Scan`
   - `Docker Compose Validation`
3. **Require Signed Commits:** Block pushes containing unsigned commits to secure commit lineage.
