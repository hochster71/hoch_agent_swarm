# Metrics System

The Prompt Control Plane monitors and evaluates operational health, security posture, and value delivery using this metrics catalog.

## North Star Metric
- **Validated Positive Production Outcomes Per Week**: Count of verified, risk-mitigated, and QA-approved tasks completed across all domains.

## Control Plane Health Metrics
- **Known Assets Reporting**: Percentage of seeded known assets reachable via local ping/API queries (Target: 100% of control/compute nodes).
- **Agent Heartbeat Health**: Number of consecutive successful telemetry heartbeats from active agent loops.
- **Model Runtime Health**: Response latency and 2xx success rate of local Ollama/LM Studio model endpoints.
- **Prompt Route Success Rate**: Percentage of prompt router runs that successfully resolved a complete prompt chain without falling back to planning mode.
- **Tool-Call Failure Rate**: Percentage of tool calls rejected by safety policies or returning errors.

## Security Metrics
- **Critical/High Findings Open**: Count of open security findings from SAST, DAST, or manual audits (Target: 0).
- **Prompt-Injection Test Pass Rate**: Percentage of red-team prompt injection test payloads successfully blocked by security filters (Target: 100%).
- **Secrets Findings**: Number of active credentials or keys flagged in codebase scans (Target: 0).
- **SBOM Freshness**: Number of days since the Software Bill of Materials was updated (Target: <= 7 days).
- **External Exposure Count**: Number of LAN ports or API endpoints exposed to the public internet (Target: 0).
- **ConMon Evidence Freshness**: Percentage of required ConMon verification logs updated within their specified cadence (Daily/Weekly/Monthly).

## Production & Delivery Metrics
- **Idea-to-Prototype Time**: Duration between logging a new feature concept and compiling the first working local prototype.
- **Prototype-to-Release Time**: Duration between completing a prototype and committing its validated release tag.
- **QA First-Pass Rate**: Percentage of code submissions that pass the full integration test suite on the first run.
- **Release-Gate Pass Rate**: Percentage of builds that satisfy release authorization criteria without failing verification checks.
- **Rework Loops per Task**: Average count of revision loops required to resolve compiler, lint, or QA failures.

## Personal & Home Metrics
- **Family/Home Automations Completed**: Number of helpful automations configured for household scheduling, dashboarding, or notifications.
- **Household Tasks Assisted**: Count of operational home-life workflows assisted by agent prompts.
- **Privacy Incidents**: Any instance of sensitive family or personal data processed by public endpoints (Target: 0).
- **Manual Time Saved**: Estimated weekly hours saved by automating repetitive personal or household administration tasks.

## Business & HASF Metrics
- **HASF Apps Shipped**: Number of completed application packages compiled, validated, and signed within the Hoch Application Software Factory.
- **Backlog Throughput**: Number of user stories or tasks completed from the backlog per sprint.
- **App-Store Packages Ready**: Count of release-candidate builds that have passed the App Store pre-submission checks.
- **Business Workflows Automated**: Count of automated workflows handling business documents, report translations, or ticket sorting.

## Hobby & Humanity Metrics
- **Positive-Impact Experiments Completed**: Count of experimental outcomes or prototypes aligned with positive AI-for-humanity goals.
- **Reusable Templates Created**: Shared prompt templates or software components published locally for reuse.
- **Community/Helpfulness Score**: Qualitative assessment of automation utility for community, family, and collaborative projects.
