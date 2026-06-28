# UI Component Inventory

This inventory documents the reusable interface components designed for the dark-theme HOCH AI OS Control Plane.

## Reusable Components

### 1. Global Navigation Header
- **Selector**: `header.global-ops-bar`
- **Visuals**: Border bottom (`--border-subtle`), background (`--bg-secondary`).
- **Features**: Left-aligned breadcrumb path, center-aligned North Star progress score, right-aligned telemetry badges (`active-assets-badge`, `sync-status-text`, `latency-val`).

### 2. Status Indicator Dot
- **Selector**: `.cockpit-indicator-dot`
- **Visuals**: 8px circular status indicator.
- **States**:
  - `.state-live`: Glow effect in cyan/green (active, operational).
  - `.state-degraded`: Glow in amber (functioning with warnings).
  - `.state-failed`: Pulse in red (error/outage).
  - `.state-pending`: Pulse in amber (human action required).
  - `.state-assumption`: Purple (unverified code posture).

### 3. Metric Badge
- **Selector**: `.badge`
- **Visuals**: Padding `4px 8px`, rounded border, monospaced text.
- **Classes**:
  - `.badge-info`: Cyan background, white text.
  - `.badge-success`: Green background.
  - `.badge-warning`: Amber background.
  - `.badge-error`: Red background.

### 4. Telemetry Card Container
- **Selector**: `.card`
- **Visuals**: Background (`--bg-secondary`), border (`--border-subtle`), border radius (`--border-radius-md`), padding `16px`. Hover state applies slight backdrop blur and scale.

### 5. Interactive Console Terminal
- **Selector**: `.console-feed`
- **Visuals**: Monospaced font (`--font-mono`), background (`#010102`), border (`--border-subtle`), padding `12px`, auto-scrolling log body, and command line input box.

### 6. Human Approval Action Drawer
- **Selector**: `.approval-drawer`
- **Visuals**: Glassmorphic modal overlay, background (`--bg-glass`), backdrop filter (`--backdrop-blur`), border (`--border-glass`).
- **Inputs**: Contains details of blocked action, validation indicators, and button triggers (`button.btn-accept` in green, `button.btn-reject` in red).
