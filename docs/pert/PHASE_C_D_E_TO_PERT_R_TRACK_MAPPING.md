# Phase C/D/E to PERT R-Track Mapping

This document reconciles Phase C, D, and E of the HAS/HASF Autonomy roadmap against the PERT v2 R-Track (Runtime Execution and Hardening).

## Mapped Nodes

1. **Phase C: Execution Autonomy**
   - Maps to **PERT R2** (Local Execution Loops).
   - Establishes pulling pending queue tasks when permitted.

2. **Phase D: Autonomy Hardening**
   - Maps to **PERT R4** (Runtime Security and Governance).
   - Establishes lease management, state transitions, policy classification, and operator hold overrides.

3. **Phase E: Autonomy Daemon Burn-In**
   - Maps to **PERT R4** (Daemon Burn-In & Fencing Validation).
   - Establishes process supervision, heartbeats, failure injection, and raw validation audits.

## K-Track Critical-Path Alignment

- The K-track (Knowledge Graph and Agent Flight Deck) runs parallel to the R-track.
- Autonomy lanes must not orphan K-track.
- Critic seats and founder keys remain the primary veto system over autonomous actions.
