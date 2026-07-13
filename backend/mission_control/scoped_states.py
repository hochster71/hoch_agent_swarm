"""HELM Scoped States.

Defines the explicit state levels and propagation logic:
- GLOBAL_PLATFORM_STATE
- FACTORY_STATE
- PRODUCT_STATE
- MISSION_STATE
- TASK_STATE
- EXTERNAL_GATE_STATE
- FOUNDER_GATE_STATE
"""
from __future__ import annotations
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("HELM.ScopedStates")

class ScopeLevel(str, Enum):
    GLOBAL_PLATFORM = "GLOBAL_PLATFORM_STATE"
    FACTORY = "FACTORY_STATE"
    PRODUCT = "PRODUCT_STATE"
    MISSION = "MISSION_STATE"
    TASK = "TASK_STATE"
    EXTERNAL_GATE = "EXTERNAL_GATE_STATE"
    FOUNDER_GATE = "FOUNDER_GATE_STATE"

class StateStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    FROZEN = "FROZEN"
    LOCKED = "LOCKED"
    BLOCKED = "BLOCKED"
    BLOCKED_EXTERNAL = "BLOCKED_EXTERNAL"
    ELIGIBLE = "ELIGIBLE"
    NOT_READY = "NOT_READY"
    UNKNOWN = "UNKNOWN"
    COMPLETE = "COMPLETE"

class ScopedStateEvaluator:
    """Evaluates scoped states from blockers, hold status, and validation truth."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def evaluate_states(self, global_hold: bool, blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
        # 1. Determine platform and scheduler state
        platform_state = StateStatus.ACTIVE
        scheduler_state = StateStatus.ACTIVE
        council_state = StateStatus.ACTIVE

        # Global hold or critical system failure turns scheduler/platform to FROZEN/LOCKED
        if global_hold:
            platform_state = StateStatus.FROZEN
            scheduler_state = StateStatus.LOCKED
            council_state = StateStatus.LOCKED

        # Extract blockers by ID/scope
        epic_fury_blocked = False
        for b in blockers:
            b_id = b.get("id", "")
            b_status = b.get("status", "")
            # G-7 is founder external accounts (Apple/Google), G-6 is App Store Review
            if b_id in ("G-6", "G-7") and b_status != "RESOLVED" and b_status != "PASS":
                epic_fury_blocked = True

        # Factory states: HASF (Epic Fury), others
        factory_states = {
            "HASF": {
                "state": StateStatus.BLOCKED.value if epic_fury_blocked else StateStatus.ACTIVE.value,
                "current_champion": "EPIC_FURY_2026",
                "distribution_lane": StateStatus.BLOCKED_EXTERNAL.value if epic_fury_blocked else StateStatus.ELIGIBLE.value,
                "reason": "APPLE_REVIEW_PENDING" if epic_fury_blocked else "OK",
                "agent_work": "COMPLETE" if epic_fury_blocked else "IN_PROGRESS"
            },
            "HRF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "RESEARCH_SYNTHESIS_v1",
                "distribution_lane": StateStatus.ELIGIBLE.value,
                "reason": "OK",
                "agent_work": "IN_PROGRESS"
            },
            "HCF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "CYBER_HARDENING_MANIFEST",
                "distribution_lane": StateStatus.ELIGIBLE.value,
                "reason": "OK",
                "agent_work": "IN_PROGRESS"
            },
            "HSF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "STORY_CHRONICLE_v2",
                "distribution_lane": StateStatus.ELIGIBLE.value,
                "reason": "OK",
                "agent_work": "IN_PROGRESS"
            },
            "HMF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "MUSIC_MELODY_v1",
                "distribution_lane": StateStatus.ELIGIBLE.value,
                "reason": "OK",
                "agent_work": "IN_PROGRESS"
            },
            "HFF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "UNKNOWN",
                "distribution_lane": StateStatus.NOT_READY.value,
                "reason": "NO_ACTIVE_CHAMPION",
                "agent_work": "COMPLETE"
            },
            "HHF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "UNKNOWN",
                "distribution_lane": StateStatus.NOT_READY.value,
                "reason": "NO_ACTIVE_CHAMPION",
                "agent_work": "COMPLETE"
            },
            "HPF": {
                "state": StateStatus.ACTIVE.value,
                "current_champion": "UNKNOWN",
                "distribution_lane": StateStatus.NOT_READY.value,
                "reason": "NO_ACTIVE_CHAMPION",
                "agent_work": "COMPLETE"
            }
        }

        return {
            "GLOBAL_PLATFORM_STATE": platform_state.value,
            "SCHEDULER_STATE": scheduler_state.value,
            "COUNCIL_STATE": council_state.value,
            "FACTORY_STATE": factory_states,
            "EXTERNAL_GATE_STATE": {
                "epic_fury_apple_review": "BLOCKED_EXTERNAL" if epic_fury_blocked else "CLEARED"
            },
            "FOUNDER_GATE_STATE": {
                "h1c_controlled_execution": "LOCKED"
            }
        }
