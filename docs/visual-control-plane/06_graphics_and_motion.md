# Graphics and Motion Doctrine

All animations, graphics, and transitions in the visual control plane must serve functional indicators rather than decorative overlays.

## Core System Graphics

### 1. Hybrid Control-Plane Node Map
- **Visual**: A central hub-and-spoke tree layout. The central node represents the MacBook Pro (Commander). Radiating lines connect to the iMac, NEO, Dell, and iPads/iPhone.
- **States**: Connection lines change color based on health: solid cyan for online, dashed red for offline.

### 2. Agent Constellation Map
- **Visual**: Space-themed nodes connected by thin white paths, representing active domains. Selecting a domain expands its node, showing active tasks.

### 3. Prompt Routing Graph
- **Visual**: Flow chart tracing the lifecycle of a prompt: user goal input -> risk classifier -> prompt registry -> universal contract wrapper -> agent execution -> evidence collector -> human approval.

### 4. Application Factory Conveyor Pipeline
- **Visual**: A horizontal track with 11 milestone slots. As a build moves through phases, the active slot highlights and pulses.

## Functional Motion Guidelines

### 1. Heartbeat Pulse
- **Usage**: Active agents displaying in the dashboard cards.
- **Effect**: Subtle opacity change (`opacity: 1` to `opacity: 0.6`) with a period of `2s` (`cubic-bezier(0.4, 0, 0.2, 1)`).

### 2. Probing Scan Sweep
- **Usage**: Active network scan sweeps or device rescan button animations.
- **Effect**: A linear gradient wipe from left to right with a soft white glow, repeating until the scan completes.

### 3. Build Lane Conveyor Belt
- **Usage**: Active build pipelines in the App Factory.
- **Effect**: Horizontal translate animation (`transform: translateX()`) showing tasks flowing into the next workcell.

### 4. Lock Gate Close
- **Usage**: Blocking of code changes or fail-closed state triggers.
- **Effect**: An amber/red padlock graphic slides down and snaps into place (`bounce` effect).

### 5. Constellation Line Wave
- **Usage**: Data routing or API request updates between nodes.
- **Effect**: A tiny bright particle travels along the constellation line from the commander to the worker node.

### 6. Reduced-Motion Support
When `prefers-reduced-motion: reduce` is detected via media query:
- All infinite pulses, sweeps, and particles are deactivated.
- Transitions default to instant opacity fades (`duration: 50ms`).
