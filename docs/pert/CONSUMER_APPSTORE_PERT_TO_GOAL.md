# CONSUMER APP STORE PERT TO GOAL

This document outlines the PERT graph and critical path to target a live app on both Apple App Store and Google Play under the strict consumer-only strategy.

---

## 1. Task Dependency Graph

```mermaid
graph TD
  K1["K1: Key & Provider Provisioning (PASS)"]
  H1["H1: Host Access & Sync (PASS)"]
  H2["H2: Active systemd Telemetry (PASS)"]
  G1["G1: Demand Validation Gate (PENDING)"]
  G4["G4: ASO / Discovery Gate (PENDING)"]
  A2["A2: Demand Experiment Gate (PENDING)"]
  A3["A3: Product Build Phase (PENDING)"]
  A4["A4: Differentiation & Packaging (PENDING)"]
  A6["A6: Release Runner Deployment (PENDING)"]
  SUB["SUB: Store Submission (PENDING)"]
  GOAL["GOAL: App Live on Stores"]

  K1 --> H1
  H1 --> H2
  H2 --> G1
  G1 --> G4
  G4 --> A2
  A2 --> A3
  A3 --> A4
  A4 --> A6
  A6 --> SUB
  SUB --> GOAL
```

---

## 2. Track & Gate Compliance

All tasks are mapped to canonical tracks `[R, K, A, B, D]` to ensure automated policy checkers pass.

| Task ID | Track | Name | Enforced Policy / Constraint |
| --- | --- | --- | --- |
| **K1** | K | API Key Provisioning | Founder must add OpenAI/Anthropic keys |
| **H1** | K | Host Verification | ssh access and workspace sync verified |
| **H2** | K | systemd Supervision | telemetry verify check |
| **G1** | R | Demand Validation Gate | Target user, problem, and success threshold defined |
| **G4** | R | ASO / Discovery Gate | Keywords, competitor set, metadata hypothesis |
| **A2** | A | Demand Experiment Gate | Pre-build cheap landing page or waitlist check |
| **A3** | A | Build Phase | Enforce build lock |
| **A4** | A | Differentiation Gate | Apple 4.3 and Google repetitive-content check |
| **A6** | A | Release Runner | Production compilation and signing |
| **SUB** | B | App Submission | Founder-managed credentials and submission |
| **GOAL** | B | App Live on Stores | Verified public store entries |

---

## 3. Critical Path

```
K1 (PASS) → H1 (PASS) → H2 (PASS) → G1 (PENDING) → G4 (PENDING) → A2 (PENDING) → A3 (PENDING) → A4 (PENDING) → A6 (PENDING) → SUB (PENDING) → GOAL
```
**Current Blocker**: **`G1`** (Demand Validation Gate).
