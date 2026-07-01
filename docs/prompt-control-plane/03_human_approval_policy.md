# Human Approval Policy

All operations within the HOCH Agent Swarm Prompt Control Plane are bounded by this human approval policy.

## Classification of Actions

### 1. Autonomous Actions Allowed
The swarm may perform the following tasks autonomously without prior approval:
- Read local files within the approved project directory.
- Perform web searches or read public documentation pages.
- Create local documentation drafts or write proposal code.
- Run non-destructive test suites, SAST scanners, or linters.
- Generate local evidence logs, SBOMs, or candidate manifests.

### 2. Approval Required (Human-in-the-Loop Enforced)
The following actions must be blocked by the runtime scheduler and staged in the approval queue until Michael Hoch explicitly signs off:
- Deleting, renaming, or moving large project or system files.
- Changing firewall settings, exposing ports, or modifying router mappings.
- Overwriting or editing secrets, API credentials, or certificates.
- Launching external network integrations, webhook relays, or tunnels.
- Spending money, processing purchases, or triggering paid APIs.
- Sending email alerts or messages outside the local network.
- Submitting app packages to App Stores or external registries.
- Modifying model lifecycle states (e.g. promoting or quarantining models).
- Committing/merging code directly to main/release branches.

### 3. Prohibited Actions
These operations are completely blocked and must result in immediate fail-closed:
- Disabling the audit logger or clearing the swarm event bus.
- Weakening firewall, SSL/TLS, or sandbox container limits.
- Injecting third-party scripts or libraries without provenance verification.
- Inventing or falsifying security scan evidence.
- Executing destructive cleanup daemons on live production filesystems.

## Core Human-in-the-Loop Gates

### Michael Hoch Final Approval Gate
The absolute authority for any action marked as "Approval Required". The control plane UI mounts an interactive queue where actions must be reviewed and approved.

### App Store Submission Gate
Before any binary build is pushed to TestFlight, Apple App Store, or Google Play, a complete verification report and signature manifest must be reviewed.

### Destructive-Action Gate
Any file deletion or destructive cleanup candidate must be signed with the exact phrase confirmation.

### Security-Posture-Change Gate
Any alteration to system configs, ports, or encryption requires a validated regression test and human audit.

### External-Publication Gate
No content, code repository, or documentation may be pushed to public Github organizations or websites without manual review.

### Model Deletion/Quarantine Gate
Quarantining or deleting model layers requires explicit validation report checks.
