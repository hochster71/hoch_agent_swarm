# HASF Product Gate Package

This document defines the product registry, scoring standards, and compliance gates for registered App Store products.

## Product Ingestion

Every candidate product must be registered in [hasf_product_registry.json](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data/hasf_product_registry.json) and graded against the 11-filter security matrix.

## 11-Filter Security Matrix

1. **Brain Privacy**: Prevent Swarm internal prompt leaks.
2. **Egress Compliance**: Audit network calls against egress white-lists.
3. **Zero Autonomy Claims**: Ensure marketing/UI references match real burn-in logs.
4. **UI Differentiation**: Enforce unique branding.
5. **Functionality Differentiation**: Avoid duplicates.
6. **App Review Compliance**: Adhere to Guideline 2.3/2.5.
7. **Codebase Cleanliness**: Ensure no leaked credentials.
8. **Founder Precedence**: Enforce manual gating on live deployments.
9. **Dependency Security**: Static dependencies audit.
10. **E2E Compile State**: Verify local Xcode compile targets.
11. **Local Storage Sandboxing**: Verify app sandbox storage.
