# HOCH PODS Theater Design Doctrine

This document establishes the binding design rules and constraints for the HOCH PODS cinematic user interface.

## Binding Design Reference
- **Visual Reference Image**: [hoch-pods-theater-agent-liftoff-reference.jpeg](file:///Users/michaelhoch/hoch_agent_swarm/docs/design/assets/hoch-pods-theater-agent-liftoff-reference.jpeg) is the binding design reference for all HOCH PODS UI work.
- **Cinematic Presentation**: The first visible screen of the HOCH PODS panel must be the **15-step Agent Lift-Off & Integration Movie Board**, not a dashboard of cards.
- **Legacy Components**: Legacy panels (scheduler, approval, execution, leadership, etc.) may remain, but they must be rendered below the theater.

## Data-Driven Animations
- **Truthful Telemetry**: Animations must be tied to live, fresh data from `/api/pert/data`. There must be no decorative, simulated, or stale active animations.
- **Stale/Missing Freeze**: If the data source for a given pod or segment is stale or missing, the affected movie clips must visibly freeze, receive a quarantined gray/amber border overlay, and display the `STALE TELEMETRY` warning.
- **State Transition Mapping**: Pod runtime states must map directly to specific lifecycle steps on the Movie Board.

## 15-Step Agent Lift-Off & Integration Clips
The 15 clips representing the agent lifecycle are:
1. **Agent ready**: The AI agent is initialized and waiting in registry.
2. **Pod doors open**: Pod enclave allocation starts.
3. **Power up**: Enclave node provisioning and bootstrap.
4. **Launch sequence**: Pre-flight policy checks and guardrail runs.
5. **Lift off**: Model assignment binding complete.
6. **Transit tunnel**: Tool library mounting and verification.
7. **Route confirmed**: Target directory boundaries and allowlist verification.
8. **Approaching destination**: Connecting to the execute node.
9. **Docking**: Enclave authentication and mounting.
10. **Integration sync**: Telemetry pipeline handshakes.
11. **Capability link**: Access to system resources and APIs established.
12. **RACI mapping**: Validating accountability boundaries and approval status.
13. **Mission assignment**: Loading the execution proposal and details.
14. **Active in HAS**: Pod starts task execution.
15. **Flow integrated**: Results compiled, evidence written, and flows updated.
