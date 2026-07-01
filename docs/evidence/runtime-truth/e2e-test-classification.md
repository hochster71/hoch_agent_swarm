# E2E Test Classification Matrix

This document registers and classifies all 41 Playwright E2E tests in the Hoch Agent Swarm (HAS) repository to distinguish between the current live runtime dashboard and legacy/compatibility frameworks.

| Test Filename | Current Purpose | Classification | Production GO Relevance | Required Action | Notes on Stale/Fake Risk |
|---|---|---|---|---|---|
| `antigravity-runtime.spec.ts` | Verifies Antigravity console, layout modules, and safe runtime indicators | `current-runtime` | Yes | Keep | Proves live UI liveness |
| `brain-autonomy.spec.ts` | Verifies LLM Gated Autonomy panels and mode restrictions | `current-runtime` | Yes | Keep | Proves dynamic agent gating |
| `live-project-tracker.spec.ts` | Verifies project tracker checklist items and status | `current-runtime` | Yes | Keep | Core tracker panel validation |
| `live-runtime-cockpit.spec.ts` | Verifies cockpit health meters and service status badges | `current-runtime` | Yes | Keep | Core liveness telemetry |
| `runtime-reliability.spec.ts` | Asserts heartbeats and 18 critical telemetry status indicators | `current-runtime` | Yes | Keep | Core runtime truth proof |
| `theme-skinning.spec.ts` | Verifies CSS theme selectors, variable states, and skin consistency | `current-runtime` | Yes | Keep | Layout presentation gate |
| `reduced-motion-swarm.spec.ts` | Verifies accessibility (a11y) reduced-motion settings in the browser | `current-runtime` | Yes | Keep | CSS animation check |
| `full-page-swarm-audit.spec.ts` | Audits layout structure and visual completeness | `current-runtime` | Yes | Keep | Visual layout check |
| `global-swarm-animation-runtime.spec.ts` | Verifies active canvas elements and rendering performance | `current-runtime` | Yes | Keep | Performance telemetry |
| `swarm-animation-deep-audit.spec.ts` | Measures frame rates and rendering latency of canvas | `current-runtime` | Yes | Keep | Performance telemetry |
| `candidate-release-packet.spec.ts` | Legacy candidate release generation form check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `formal-release-approval.spec.ts` | Legacy operator release approval gates check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `formal-release-preview.spec.ts` | Legacy release preview checklist checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `formal-release-seal-dry-run.spec.ts` | Legacy custody seal dry-run validations | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-authority-gate.spec.ts` | Legacy release authority promotion checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-channel-governance.spec.ts` | Legacy release channel promotion rules check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-decision-room.spec.ts` | Legacy operator release decision rooms | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-evidence-archive-build-plan.spec.ts` | Legacy retention and archive build plans | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-evidence-archive-preview.spec.ts` | Legacy manifest files generation checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-evidence-archive-seal-preview.spec.ts` | Legacy retention seals verification | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-evidence-retention.spec.ts` | Legacy evidence database retention policy checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-execution-plan.spec.ts` | Legacy ordered build deployment plans | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-seal-attestation-bundle.spec.ts` | Legacy dry-run release attestation generation | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `release-signing-policy.spec.ts` | Legacy signed/unsigned waiver rule gating | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `operator-governance-cockpit.spec.ts` | Legacy overall cockpit panel checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited release panel |
| `capability-enforcement.spec.ts` | Legacy routing engine capability permissions check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `capability-routing.spec.ts` | Legacy model routing history event selection checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `device-registry-topology.spec.ts` | Legacy fleet map and cluster drawer details check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `device-service-lease.spec.ts` | Legacy lease approval status badges check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `device-service-registry.spec.ts` | Legacy service node network registry checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `model-provider-registry.spec.ts` | Legacy provider status and health check actions | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `topology-agent-overlay.spec.ts` | Legacy swarm network maps overlays checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `mesh-sentinel.spec.ts` | Legacy sentinel mesh security topology checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited routing panel |
| `crewai-ingestion-bridge.spec.ts` | Legacy execution plan parsing bridge | `legacy-compatibility` | No | Tag `@legacy` | Deorbited bridge panel |
| `evidence-graph.spec.ts` | Legacy node trace interactive elements | `legacy-compatibility` | No | Tag `@legacy` | Deorbited bridge panel |
| `finance-command-center.spec.ts` | Legacy ledger budget allocation panels | `legacy-compatibility` | No | Tag `@legacy` | Deorbited finance panel |
| `networkops_healing.spec.ts` | Legacy network self-healing diagnostics check | `legacy-compatibility` | No | Tag `@legacy` | Deorbited network panel |
| `pert-e2e-build.spec.ts` | Legacy pert build visualizer checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited PERT panel |
| `security-gate.spec.ts` | Legacy vulnerability scanners integration checks | `legacy-compatibility` | No | Tag `@legacy` | Deorbited security panel |
| `dast-unsigned-ui-negative.spec.ts` | Legacy security gate XSS/negative tests | `legacy-compatibility` | No | Tag `@legacy` | Deorbited security panel |
| `cybersecurity-factory.spec.ts` | Legacy swarm agent pipeline run checker | `legacy-compatibility` | No | Tag `@legacy` | Deorbited pipeline panel |
