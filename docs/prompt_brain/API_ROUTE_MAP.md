# HOCH Prompt Brain — API Route Map

This document maps all FastAPI endpoints in `backend/main.py` dedicated to the Prompt Brain Factory.

| Method | Endpoint Route | Purpose | Backing Data File | Demo Relevance |
|---|---|---|---|---|
| `GET` | `/api/prompt-brain/adapters/health` | Model Engine Health Checks | None | Verifies Ollama/LM Studio connectivity |
| `GET` | `/api/prompt-brain/adapters/discovery` | Model Engine Catalog | None | Displays loaded model metadata |
| `GET` | `/api/prompt-brain/benchmarks/live` | Live Benchmarking Stats | `scoring_trace.jsonl` | Proves win rate metrics |
| `GET` | `/api/prompt-brain/benchmarks/unseen` | Unseen Benchmark Results | `unseen_benchmarks.jsonl` | Validates model performance on new tasks |
| `GET` | `/api/prompt-brain/benchmarks/messy-input` | Messy Evidence validation | `messy_inputs_validation.jsonl` | Evaluates accuracy under noisy evidence |
| `GET` | `/api/prompt-brain/demo/scenarios` | Sanitized Scenarios List | `sanitized_demo_dataset.json` | Mounts the demo workspace |
| `GET` | `/api/prompt-brain/outreach/targets` | Shortlist Profiles | `target_account_shortlist.md` | Tracks target outreach list |
| `GET` | `/api/prompt-brain/outreach/queue` | Approval Queue | `outreach_queue.jsonl` | Pre-transmission staging registry |
| `POST` | `/api/prompt-brain/outreach/approve` | Manual Operator Approval | `outreach_approval_log.jsonl` | Zero-leakage compliance confirmation |
| `POST` | `/api/prompt-brain/outreach/feedback` | Record Evaluator Scores | `reviewer_feedback_log.jsonl` | Updates average trust score |
| `GET` | `/api/prompt-brain/outreach/signals` | Buyer Metrics Summary | `buyer_signal_dashboard.json` | Visualizes responses and demo schedules |
| `GET` | `/api/prompt-brain/pilot/paid-offer` | Pilot Cohort Agreement Docs | `paid_pilot_offer.md` | Displays cohort deliverables |
| `GET` | `/api/prompt-brain/pilot/pricing` | Pricing models | `pricing_model.json` | Starter and GovCon pricing options |
| `GET` | `/api/prompt-brain/pilot/pipeline` | Active Lead Tracker | `paid_pilot_pipeline.json` | Displays lead pipelines |
| `GET` | `/api/prompt-brain/pilot/conversion` | Conversion summary metrics | `pilot_conversion_tracker.json` | Tracks expected pipeline value |
| `POST` | `/api/prompt-brain/pilot/conversion` | Modify lead pipeline status | `pilot_conversion_tracker.json` | Transition leads in pipeline |
| `GET` | `/api/prompt-brain/pilot/risks` | Risk Register details | `pilot_risk_register.json` | Pre-screens installation blockers |
| `GET` | `/prototype/prompt-brain` | Command Center Frontend | None | Interactive UI cockpit |
