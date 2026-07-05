# CONSUMER APP STORE GATE MODEL

This document details the executable gates that enforce the consumer app-store strategy (Apple App Store + Google Play) for HASF.

---

## Gate 1: Demand Validation (G1)
- **Objective**: Block any development work (A3) until product market demand is defined.
- **Enforcement Rules**:
  - `target_user_defined`: must identify target consumer audience.
  - `painful_problem_defined`: must articulate the core painful problem.
  - `existing_alternatives_defined`: must detail how users currently cope.
  - `test_method_defined`: must establish the testing parameters.
  - `success_threshold_defined`: must set numerical validation targets.
- **Allowed Verdicts**: `DEMAND_GATE_PASS`, `DEMAND_GATE_PENDING`, `DEMAND_GATE_NO_GO`.

---

## Gate 2: Differentiation (G2)
- **Objective**: Prevent template/clone app rejections (Apple 4.3 / Google Repetitive Content).
- **Enforcement Rules**:
  - `unique_user_value`: clear consumer utility.
  - `differentiated_workflow`: non-generic interaction flows.
  - `differentiated_ui`: unique style, not matching stock templates.
  - `original_branding`: custom visual identity.
  - `non_duplicate_store_listing`: original marketing copy and assets.
- **Allowed Verdicts**: `DIFFERENTIATION_PASS`, `DIFFERENTIATION_PENDING`, `DIFFERENTIATION_NO_GO`.

---

## Gate 3: Retention Instrumentation (G3)
- **Objective**: Measure engagement patterns before scaling.
- **Enforcement Rules**:
  - `activation_event_defined`: metric for user setup success.
  - `retention_event_defined`: metric for repeated usage.
  - `day_1_7_30_metrics_defined`: clear retention cohorts.
  - `churn_signal_defined`: indicators of user dropoff.
  - `feedback_capture_defined`: mechanism for user reviews.
- **Allowed Verdicts**: `RETENTION_READY`, `RETENTION_PENDING`, `RETENTION_NO_GO`.

---

## Gate 4: ASO / Discovery (G4)
- **Objective**: Define visibility strategy ahead of launch.
- **Enforcement Rules**:
  - `keyword_set_defined`: high-intent search terms.
  - `competitor_set_defined`: benchmark store entries.
  - `title_subtitle_hypothesis`: metadata layout.
  - `screenshots_message_test`: conversion rate optimization.
  - `discovery_channel_defined`: organic or viral loops.
- **Allowed Verdicts**: `DISCOVERY_READY`, `DISCOVERY_PENDING`, `DISCOVERY_NO_GO`.

---

## Gate A2: Demand Experiment (A2)
- **Objective**: Execution-level check to confirm validation experiment ran before build.
- **Enforcement Rules**:
  - `experiment_executed`: landing page, waitlist, concierge test, or survey.
  - `evidence_produced`: structured logs/feedback dataset.
  - `success_threshold_met`: conversion/interest rate validated.
- **Allowed Verdicts**: `DEMAND_SIGNAL_GREEN`, `DEMAND_SIGNAL_AMBER`, `DEMAND_SIGNAL_RED`.

---

## Schema Reference

The executable machine-readable states are managed in:
[consumer_appstore_gate_model.json](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data/consumer_appstore_gate_model.json)
