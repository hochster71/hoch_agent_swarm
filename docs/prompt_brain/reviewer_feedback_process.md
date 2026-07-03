# HOCH Prompt Brain — Reviewer Feedback Process

This document details how external reviewer evaluations are captured, logged, and processed.

---

## 1. Feedback Ingestion Route
Reviewers fill out the scoring form (Tab 10 dashboard) or submit their JSON review file. Submissions are routed to the `POST /api/prompt-brain/pilot/feedback` endpoint and appended to [reviewer_feedback_log.jsonl](file:///Users/michaelhoch/hoch_agent_swarm/data/prompt_brain/demo/reviewer_feedback_log.jsonl).

---

## 2. Threshold Escalation Rules
* **Low Trust Alert**: If an evaluator records a `trust_score` below 7.0, an automated engineering ticket is spawned to review the prompt template.
* **Hallucination Flags**: Any entry listing active `hallucination_concerns` blocks the template version from moving to production release status.

---

## 3. Pilot Conversion Flow
* If `willingness_to_pilot_signal` is `true`, add the reviewer's organization to the pilot outreach sequence.
