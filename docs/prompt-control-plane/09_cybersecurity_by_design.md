# Cybersecurity by Design

This document describes the security controls and alignment mappings designed into the Prompt Control Plane.

## Security Framework Alignment

### NIST SSDF Alignment (SP 800-218)
- **Prepare the Organization (PO)**: Establish the Universal Agent Execution Contract as the baseline safety gate.
- **Protect the Software (PS)**: Utilize code signing, verification manifests, and dependency scanning.
- **Produce Secure Software (PW)**: Integrate automated SAST, linter checks, and QA scripts.
- **Respond to Vulnerabilities (RV)**: Maintain a risk register and run automated validation tests.

### NIST AI Risk Management Framework (AI RMF 1.0)
- **Govern**: Establish policies for human approval, data collection boundaries, and operational scopes.
- **Map**: Analyze risks regarding prompt injection, sensitive data leakage, and excessive agency.
- **Measure**: Run test suites evaluating model outputs against benchmark thresholds.
- **Manage**: Enforce fail-closed controls, quarantining underperforming models.

### OWASP Top 10 for LLM Applications
- **LLM01: Prompt Injection**: Red-team test suites evaluate inputs before prompt wrapping.
- **LLM02: Insecure Output Handling**: All outputs are parsed against strict Pydantic structures.
- **LLM06: Sensitive Information Disclosure**: Input scanning and redaction guards block private telemetry from being exposed.
- **LLM08: Excessive Agency**: Strict tool-use authorization boundaries restrict write/network scopes.
- **LLM09: Overreliance**: Human approval required for all material operations.

### Supply Chain Levels for Software Artifacts (SLSA)
- **Provenance**: Dynamic generation of SBOMs (`sbom.spdx.json`) and provenance logs (`provenance.intoto.jsonl`).
- **Build Integrity**: Builds are compiled in isolated spaces and verified with SHA-256 checks.

## Key Controls

### Secrets Scanning
Automated repository scans detect hardcoded keys or credentials prior to git commits.

### SAST/SCA/DAST
Static analysis, dependency checking, and dynamic endpoint scanning execute prior to release.

### Prompt Injection Testing
Simulated injection attacks are run against routers to prevent command hijack.

### Excessive Agency Controls
Agents are decoupled from destructive capabilities; credentials or system configurations cannot be altered by LLM loops.

### Tool-Use Authorization
Allowed tools are scoped per agent role. Arbitrary code execution is confined to isolated environments.

### Audit Logging
All transactions are logged to `swarm_ledger.db` and preserved in the event log.

### Model Lifecycle Governance
Model evaluation promotes, quarantines, or blocks models based on task performance metrics.

### Local Network Security
Nodes are authenticated inside the LAN. No general external ingress is allowed.

### Fail-Closed Controls
Failure of security validations halts the pipeline immediately and blocks release.
