# Visual Control Plane Implementation Roadmap

This roadmap details the phased milestones to implement the dark-theme UI.

## Phase V0: Visual Doctrine & Blueprints
- **Objective**: Seed the design tokens, page maps, agent cards, and graphics specifications.
- **Exit Criteria**: All 11 markdown files and the JSON config pass QA validation.
- **Release Gate**: CONDITIONAL GO (documentation only).

## Phase V1: Static HTML/CSS Mockups
- **Objective**: Create static index and layout templates for the main pages.
- **Exit Criteria**: HTML templates load in the browser and apply visual tokens correctly.

## Phase V2: Reusable Component Library
- **Objective**: Extract common styling (navbars, card grids, indicator lights) into a central stylesheet.
- **Exit Criteria**: All common layout items inherit styles from the design token system.

## Phase V3: Data-Bound Telemetry Cards
- **Objective**: Hook the FastAPI cockpit payload (`/api/v1/live-runtime/cockpit`) to update dashboard elements.
- **Exit Criteria**: Live indicators and card metrics match the backend API values.

## Phase V4: Agent Gallery & Prompt Registry Visuals
- **Objective**: Integrate prompt list JSON to render agent cards with metadata.
- **Exit Criteria**: The 103 prompts can be filtered and inspected in the UI.

## Phase V5: Control-Plane Node Map Visualizations
- **Objective**: Implement the SVG tree map connecting active hosts and model runtimes.
- **Exit Criteria**: Interactive spokes update colors depending on host ping statuses.

## Phase V6: App Factory assembly-line Pipelines
- **Objective**: Build the horizontal conveyor visualization showing active build progress.
- **Exit Criteria**: Active build lanes move across cells dynamically.

## Phase V7: Cybersecurity & ConMon Auditing Indicators
- **Objective**: Implement visual tables and checkers for open findings and checklist status.
- **Exit Criteria**: Metric cards update depending on the latest local port/SAST check.

## Phase V8: Visual QA & Accessibility Auditing
- **Objective**: Execute accessibility evaluations for contrast, keyboard focus, and screen-readers.
- **Exit Criteria**: Pass automated axe/a11y scanner checks.

## Phase V9: Production UI Seal
- **Objective**: Compile and minify production bundles, sign files, and freeze UI assets.
- **Exit Criteria**: Clean working tree and passing CI pipeline checks.
