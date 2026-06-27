# Visual Control Plane Component Library

This document specifies the 14 reusable components defined for the dark-theme visual control plane.

---

## 1. ops-header
*   **Purpose**: Global navigation bar providing structural context.
*   **Required Fields**: System title, Breadcrumbs, Current navigation state.
*   **Allowed States**: `LIVE`, `DEGRADED`, `PENDING`, `SIMULATED`, `STALE`, `FAIL-CLOSED`, `UNAVAILABLE`, `UNKNOWN`.
*   **Accessibility Requirements**: Must use semantic `<header>` wrapper, `nav` landmark, and high contrast (WCAG 2.2 contrast ratio > 4.5:1).
*   **Sample Markup**:
    ```html
    <header class="global-ops-bar">
      <h1>HOCH SWARM COCKPIT</h1>
      <div class="breadcrumbs"><span>RUNNING</span></div>
    </header>
    ```
*   **Failure/Empty State**: Title default fallback with `UNKNOWN` status label.
*   **Evidence Binding Requirement**: Future dynamic binding must link to `/api/v1/live-runtime/cockpit` system state.

---

## 2. status-pill
*   **Purpose**: Standardized badge representing the state of an asset, process, or endpoint.
*   **Required Fields**: Label text.
*   **Allowed States**: `LIVE`, `DEGRADED`, `PENDING`, `SIMULATED`, `STALE`, `FAIL-CLOSED`, `UNAVAILABLE`, `UNKNOWN`.
*   **Accessibility Requirements**: States must not rely on color alone. Use text/labels inside the badge. Focusable if interactive.
*   **Sample Markup**:
    ```html
    <span class="status-badge status-live">LIVE</span>
    ```
*   **Failure/Empty State**: Renders as `UNKNOWN` status badge.
*   **Evidence Binding Requirement**: Must match the runtime status payload of the monitored endpoint.

---

## 3. telemetry-card
*   **Purpose**: Displays specific system metric facts.
*   **Required Fields**: Title, State Badge, Fact lines, Source label.
*   **Allowed States**: All 8 state labels.
*   **Accessibility Requirements**: Group content using a logical visual container with high contrast text.
*   **Sample Markup**:
    ```html
    <div class="card">
      <h3>SIEM Detections <span class="status-badge status-live">LIVE</span></h3>
      <div class="card-body"><p>Count: 0</p></div>
      <div class="card-source"><span>Source: siem</span></div>
    </div>
    ```
*   **Failure/Empty State**: Displays "No telemetry metrics reported" with `UNAVAILABLE` status.
*   **Evidence Binding Requirement**: Future mapping requires direct JSON link in `card-source`.

---

## 4. agent-card
*   **Purpose**: Displays agent identity, assigned role, prompt ID, and risk level.
*   **Required Fields**: Role Title, Status, Prompt ID, Risk Level, Approval Gate, Evidence Status, Loop Phase.
*   **Allowed States**: All 8 state labels.
*   **Accessibility Requirements**: Clear dt/dd structural list matching card layout. Focus outline on tabs.
*   **Sample Markup**:
    ```html
    <div class="agent-card builder-architect">
      <div class="agent-header">
        <h4>Full-Stack Builder Agent</h4>
        <span class="status-badge status-live">LIVE</span>
      </div>
      <div class="agent-details">
        <div><dt>Prompt ID</dt><dd>CODE-002</dd></div>
        <div><dt>Risk Level</dt><dd><span class="risk-badge risk-low">LOW</span></dd></div>
      </div>
    </div>
    ```
*   **Failure/Empty State**: Gray border indicating inactive / unassigned role.
*   **Evidence Binding Requirement**: Binds to `/api/v1/prompts/registry/{prompt_id}`.

---

## 5. approval-card
*   **Purpose**: Action gate requiring signature or exception waiver.
*   **Required Fields**: Action description, Status badge, Approve/Deny buttons or waiver status.
*   **Allowed States**: `PENDING`, `FAIL-CLOSED`, `LIVE`, `UNKNOWN`.
*   **Accessibility Requirements**: Focus states required for all button actions. Confirm dialog targets.
*   **Sample Markup**:
    ```html
    <div class="approval-card">
      <h4>Operator Action Needed</h4>
      <button>APPROVE</button>
    </div>
    ```
*   **Failure/Empty State**: Shows "No pending approvals".
*   **Evidence Binding Requirement**: Binds to `/api/approval/requests`.

---

## 6. evidence-card
*   **Purpose**: Represents signed release metadata, SBOM, or provenance files.
*   **Required Fields**: Attestation type, Hash, Signer, Status badge.
*   **Allowed States**: `LIVE`, `STALE`, `FAIL-CLOSED`, `UNKNOWN`.
*   **Accessibility Requirements**: Preformatted code block with high contrast.
*   **Sample Markup**:
    ```html
    <div class="evidence-card">
      <h3>Release Attestation <span class="status-badge status-live">LIVE</span></h3>
    </div>
    ```
*   **Failure/Empty State**: Displays "No evidence packets archived" with `UNAVAILABLE`.
*   **Evidence Binding Requirement**: Binds to `/api/v1/release/signing-policy`.

---

## 7. pipeline-stage
*   **Purpose**: Visual step in the conveyor line pipeline.
*   **Required Fields**: Stage name, Status text (PASS/FAIL/ACTIVE/PENDING).
*   **Allowed States**: `LIVE`, `PENDING`, `FAIL-CLOSED`, `UNKNOWN`.
*   **Accessibility Requirements**: High-contrast outline showing visual sequence flow.
*   **Sample Markup**:
    ```html
    <div class="pipeline-stage pass">
      <strong>Research</strong>
    </div>
    ```
*   **Failure/Empty State**: Grayed out label.
*   **Evidence Binding Requirement**: Binds to pipeline status ledger.

---

## 8. node-map-card
*   **Purpose**: Renders the network topography or active cluster device list.
*   **Required Fields**: Device names, IP addresses, Connection status.
*   **Allowed States**: `LIVE`, `DEGRADED`, `UNAVAILABLE`.
*   **Accessibility Requirements**: Focus target elements, text fallback representation.
*   **Sample Markup**:
    ```html
    <div class="node-map-card">
      <h3>Active Cluster Topography</h3>
    </div>
    ```
*   **Failure/Empty State**: Displays "No connected nodes found".
*   **Evidence Binding Requirement**: Binds to `/api/v1/swarm/devices`.

---

## 9. prompt-card
*   **Purpose**: Displays prompt registry items.
*   **Required Fields**: Prompt ID, Title, Status badge.
*   **Allowed States**: `LIVE`, `STALE`, `UNKNOWN`.
*   **Accessibility Requirements**: High contrast mono-font block.
*   **Sample Markup**:
    ```html
    <div class="prompt-card">
      <strong>CODE-001 (Principal Software Architect)</strong>
    </div>
    ```
*   **Failure/Empty State**: Displays "No prompt loaded".
*   **Evidence Binding Requirement**: Binds to `/api/v1/prompts/registry/{id}`.

---

## 10. risk-badge
*   **Purpose**: Displays task or prompt risk categorization.
*   **Required Fields**: Severity label (LOW, MEDIUM, HIGH, CRITICAL).
*   **Allowed States**: Matches risk classifications.
*   **Accessibility Requirements**: Colors combined with bold labels. Focusable if interactive.
*   **Sample Markup**:
    ```html
    <span class="risk-badge risk-low">LOW</span>
    ```
*   **Failure/Empty State**: Default to `LOW` risk.
*   **Evidence Binding Requirement**: Resolved from Prompt Router plan payload.

---

## 11. state-registry
*   **Purpose**: Container detailing all valid system states.
*   **Required Fields**: List of 8 status pills.
*   **Allowed States**: Static container representing all states.
*   **Accessibility Requirements**: High-contrast styling.
*   **Sample Markup**:
    ```html
    <div class="card"><h3>State Registry</h3></div>
    ```
*   **Failure/Empty State**: N/A.
*   **Evidence Binding Requirement**: Binds to `/config/visual_control_plane.json`.

---

## 12. terminal-panel
*   **Purpose**: Interactive or static console logs mockup.
*   **Required Fields**: Log text lines, Timestamp.
*   **Allowed States**: `LIVE`, `UNKNOWN`, `DEGRADED`.
*   **Accessibility Requirements**: Accessible scrollable container. Mono typeface.
*   **Sample Markup**:
    ```html
    <div class="terminal-panel"><div>INFO: Started</div></div>
    ```
*   **Failure/Empty State**: Displays "No active stdout logs".
*   **Evidence Binding Requirement**: Binds to system stderr/stdout stream.

---

## 13. metric-strip
*   **Purpose**: Horizontal row showing key counters.
*   **Required Fields**: Label, Value, Color-state.
*   **Allowed States**: `LIVE`, `DEGRADED`, `UNKNOWN`.
*   **Accessibility Requirements**: Flex grid structure matching visual order.
*   **Sample Markup**:
    ```html
    <div class="metric-strip"><div>Counters</div></div>
    ```
*   **Failure/Empty State**: Zeroed counts.
*   **Evidence Binding Requirement**: Must aggregate telemetry from multiple sources.

---

## 14. section-rail
*   **Purpose**: Vertical navigation list mapping the sub-pages.
*   **Required Fields**: Link titles, Anchors.
*   **Allowed States**: Active/Inactive links.
*   **Accessibility Requirements**: Keyboard navigable list elements.
*   **Sample Markup**:
    ```html
    <div class="section-rail"><a href="#">Link</a></div>
    ```
*   **Failure/Empty State**: Standard home map fallback.
*   **Evidence Binding Requirement**: Binds to page map structure.
