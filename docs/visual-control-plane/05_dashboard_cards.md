# Dashboard Telemetry Cards

This document outlines the visual layout blocks and telemetry properties for the key cockpit monitoring cards.

## Cockpit Card Inventory

### 1. Control Plane Status Card
- **Grid Location**: Top Left
- **Header**: Control Plane Mode
- **Body**: Displays commander IP (`10.0.0.6`), status (`GO`), active sync metrics, and current system latency (ms).
- **indicator**: `.state-live` (cyan)

### 2. Known Assets Reporting Card
- **Grid Location**: Top Row, Center-Left
- **Header**: Known Assets Mesh
- **Body**: Lists total assets (9), active/pingable count (4), and offline count (5).
- **Indicator**: `.state-degraded` (amber) because 5 mobile assets are asleep.

### 3. Model Runtime Health Card
- **Grid Location**: Top Row, Center-Right
- **Header**: Discovered Runtimes
- **Body**: Lists active engines (e.g. `Ollama (10.0.0.207):11434`, `iMac (10.0.0.241):11434`), and proven active counts.
- **Indicator**: `.state-live` (green)

### 4. Prompt Router Status Card
- **Grid Location**: Middle Row, Left
- **Header**: Prompt Control Plane
- **Body**: Displays router state, default routing policy ("Local First"), and active chains selected.
- **Indicator**: `.state-live` (violet)

### 5. Agent Loop State Card
- **Grid Location**: Middle Row, Center
- **Header**: Swarm Execution Loop
- **Body**: Shows current active loop state (e.g. `QA`, `DEVELOP`), active task ID, and execution duration.
- **Indicator**: `.state-live` (cyan)

### 6. Human Approval Queue Card
- **Grid Location**: Middle Row, Right
- **Header**: Decision Gate
- **Body**: Displays number of pending requests in approval queue, and highlights highest risk blocked action.
- **Indicator**: `.state-pending` (amber) if items are in queue; `.state-live` (green) if empty.

### 7. Fail-Closed Events Card
- **Grid Location**: Bottom Row, Left
- **Header**: Fail-Closed Monitor
- **Body**: List of blocked tasks due to safety policy exceptions or validation test failures.
- **Indicator**: `.state-live` (green) if 0 active blocks; `.state-failed` (red) if blocked.

### 8. Cyber Risk & Open Findings Card
- **Grid Location**: Bottom Row, Center-Left
- **Header**: Security & Hardening
- **Body**: Displays the number of open critical/high vulnerabilities (0), and ports audited (13).
- **Indicator**: `.state-live` (green)

### 9. Evidence Freshness Card
- **Grid Location**: Bottom Row, Center-Right
- **Header**: Evidence Vault
- **Body**: Count of verified controls (56), tests passing (94/94), and timestamp of latest evidence manifest.
- **Indicator**: `.state-live` (green)

### 10. ConMon Status Card
- **Grid Location**: Bottom Row, Right
- **Header**: Continuous Compliance
- **Body**: Daily (100%), Weekly (100%), and Monthly (100%) checklist checks pass rate.
- **Indicator**: `.state-live` (green)
