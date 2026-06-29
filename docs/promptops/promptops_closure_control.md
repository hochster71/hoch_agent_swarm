# PromptOps Closure Control Plane Reference

This document outlines the architecture, data flow, and verification lifecycle of the PromptOps Closure Control Plane in the Hoch Agent Swarm (HAS).

## System Flow

```mermaid
graph TD
    A[Operator Prompt Input] --> B[PromptClassifier]
    B --> C[PromptScorecard]
    C --> D[FakeCompletionRisk Detector]
    D --> E[PromptRewriter / Contract Generation]
    E --> F[Gate Binder]
    F --> G[Runtime Truth State Update]
    G --> H[Verification Gate checks]
```
