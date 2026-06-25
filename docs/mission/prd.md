# Product Requirements Document (PRD) — HOCH Swarm Console

**Document ID**: PRD-SWARM-2026-06-25  
**Frameworks**: Jobs To Be Done (JTBD), Kano Model  
**Author**: Product Strategy Agent  

---

## 1. Executive Summary
The HOCH Swarm Console serves as an interactive mission control dashboard for visualizing, monitoring, and orchestrating a multi-agent developer network. To handle complex development tasks with full-production reliability, the console must support a diverse roster of 14 specialized agents, represent their profiles in an interactive, premium "holographic patent trading card" interface, and track cluster telemetry in real-time.

---

## 2. Jobs To Be Done (JTBD)

- **Job 1 (Orchestration)**: *When I launch a complex multi-stage software build, I want to decompose it into dependent tasks and assign them to specialized agents, so that the work is executed efficiently and in the correct logical sequence.*
- **Job 2 (Transparency)**: *When the swarm is actively executing commands, I want to see a live visual representation of which agent is running, on what node, and with what latency, so that I can diagnose bottlenecks and monitor health.*
- **Job 3 (Inspection)**: *When reviewing agent assignments, I want to inspect their capabilities, tiers, and stats in an interactive format, so that I can understand their design parameters and readiness.*
- **Job 4 (Security)**: *When high-risk or destructive commands are requested by the swarm, I want a strict approval gate, so that I can verify safety before execution.*

---

## 3. Kano Model Analysis

### Must-Haves (Basic Expectations)
- **Agent Registry**: A clean list of all available agents, their system roles, and default phases.
- **Task Graph Viewer**: A visual breakdown of active tasks showing status (Pending, Executing, Completed, Blocked).
- **Execution Log**: A scrollable ledger of execution steps and console outputs.

### Performance Requirements (Linear Satisfaction)
- **Live WebSocket Telemetry**: High-frequency streaming of CPU, memory, and active connections.
- **Latency Monitoring**: Dynamic node ping tracking to ensure low network latency.
- **Error Budget Enforcement**: Tracking and visual rendering of the remaining error budget for autonomous actions.

### Delighters (Excitement Features)
- **Holographic Patent Trading Cards**: 3D mouse hover perspective tilt (`rotateX` / `rotateY`) and sweeping diagonal sheen effects on agent profile modals.
- **Cybernetic SVG Enhancements**: Stick figures that light up with glowing visors, joint connection nodes, and circuitry lines when active.
- **Staggered Skill Animations**: Staggered spinning and scaling effects as specialized skills load on the agent cards.

---

## 4. Roster of 14 Specialized Swarm Agent Roles

The console supports 14 specialized agent definitions:

1. **Executive Orchestrator Agent (Boss Noodle)**: Oversees swarm status, coordinates tasks, decomposes goals.
2. **Repository Recon Agent (Dr. Signal)**: Scans codebase, checks structure, inventories files.
3. **Product Strategy Agent**: Translates prompts into requirements, writes PRDs.
4. **System Architecture Agent (Prof. Blueprint)**: Designs components, draws UML/Mermaid, writes ADRs.
5. **Agent Runtime Engineer**: Builds execution loops, solves task DAGs, runs node hooks.
6. **Frontend Swarm UI Agent**: Designs responsive layouts, WebGL canvas, 3D cards, CSS micro-animations.
7. **Backend Platform Agent**: Mounts FastAPI routes, handles WebSockets, structures SQLite migrations.
8. **DevSecOps Agent**: Hardens pipeline environments, constructs Docker images, writes GitHub Actions.
9. **Cybersecurity Threat Model Agent (Capt. Guardrail)**: Audits commands, performs STRIDE threat analysis.
10. **QA and Verification Agent (Ms. Checkmark)**: Writes E2E Playwright scripts, validates contract checks.
11. **Documentation Agent**: Compiles setup manuals, runbooks, and developer onboarding guides.
12. **Research and Benchmark Agent**: Searches academic resources, compares framework performances.
13. **Governance and Compliance Agent**: Monitors audit trails, maps regulatory controls.
14. **Release Manager Agent (Eng. Rocket)**: Decides final release readiness, packages SBOM/provenance.

---

## 5. Holographic Trading Card Requirements
Each agent card must be visually premium:
- **Card Tiers**: classified into `GOLD`, `PLATINUM`, `LEGENDARY`, and `MYTHIC` with distinct color-coded glowing borders.
- **Power Stats**: Displays 4 attributes: Intelligence (INT), Speed (SPD), Reliability (REL), and Energy Cost (NRG). Bars must dynamically fill on card mount.
- **Skills Showcase**: Skills display as capsule tags that spin and scale with a staggered delay.
- **Interactive Tilt**: Mouse movements calculate cursor relative offset to apply exact 3D transformations.
