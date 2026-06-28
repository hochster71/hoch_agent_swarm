# Prompt Router Policy

The Prompt Router selects and sequences prompt chains from the Prompt Library based on the target task category, metadata, and risk profile.

## Routing Mechanism
Prompts are selected dynamically by the following keys:
- `id`
- `category`
- `industry`
- `title`

## Pipeline Chain Definitions

### Coding Tasks
When a coding task is detected, it is routed through the following specialist agent sequence:
1. **Architect**: Designs the changes and updates implementation plan docs.
2. **Builder**: Writes and modifies code according to the architecture.
3. **SAST**: Scans files for vulnerabilities, syntax errors, and anti-patterns.
4. **QA**: Executes unit and integration tests to verify requirements.
5. **Release Gatekeeper**: Validates evidence and marks build ready.

### Cybersecurity Tasks
When a security task is initiated, the routing chain is:
1. **Threat Modeler**: Identifies vectors and threats.
2. **SAST/DAST**: Runs static analysis and dynamic endpoint scans.
3. **Control Gap Analyst**: Maps findings to NIST SP 800-53 controls.
4. **ConMon Auditor**: Adds checks to the continuous monitoring log.

### Personal, Home, and Family Data Tasks
For sensitive private/family workflows, data routing includes:
1. **Privacy Engineer**: Evaluates data storage and masking.
2. **Safety Reviewer**: Validates content limits and safety rules.
3. **Human Approval Gate**: Intercepts and requires Michael Hoch approval.

### App Store / Release Tasks
For production deployments and store builds:
1. **QA Auditor**: Confirms code freeze and validation tests.
2. **Security Certifier**: Confirms SBOM, provenance, and signature hashes.
3. **Evidence Gatherer**: Generates release artifacts.
4. **Human Approval Gate**: Final human check-off.

### Ambiguous Tasks
If the incoming requirement is fuzzy or under-specified:
1. **Planner**: Creates an exploratory roadmap.
2. **Researcher**: Queries codebases, documentation, or network.
3. **Risk Classifier**: Measures the safety risk score.

### Prompt Injection / Tool Misuse Risks
If the input contains external/untrusted content or user-supplied parameters:
1. **Red Team Prompt Agent**: Evaluates the input against injection payloads.
2. **Build Breaker**: Halts execution if potential misuse is detected.
3. **Human Approval**: Routes to the dashboard queue for evaluation.

### Production-Impacting Tasks
Any task modifying server routes, persistent databases, or system boundaries:
1. **Release Readiness Gatekeeper**: Validates release manifest.
2. **Michael Hoch Approval**: Requires manual click-through on the cockpit dashboard.
