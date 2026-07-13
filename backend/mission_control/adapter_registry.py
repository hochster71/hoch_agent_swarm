"""HELM Adapter Registry.

Defines, hardens, and classifies all model/tool adapters.
"""
from __future__ import annotations
import json
import os
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("HELM.AdapterRegistry")

class EgressClass(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    EXTERNAL_RESTRICTED = "EXTERNAL_RESTRICTED"
    EXTERNAL_FRONTIER = "EXTERNAL_FRONTIER"

class AdapterCapability(str, Enum):
    TEXT = "text"
    REASONING = "reasoning"
    TOOLS = "tools"
    VISION = "vision"

class AdapterRecord:
    def __init__(
        self,
        adapter_id: str,
        name: str,
        egress_class: EgressClass,
        capabilities: List[AdapterCapability],
        input_cost_per_1m: float,
        output_cost_per_1m: float,
        context_limit: int,
        timeout_seconds: int,
        auth_required: bool,
        api_key_env_var: Optional[str] = None
    ):
        self.adapter_id = adapter_id
        self.name = name
        self.egress_class = egress_class
        self.capabilities = capabilities
        self.input_cost_per_1m = input_cost_per_1m
        self.output_cost_per_1m = output_cost_per_1m
        self.context_limit = context_limit
        self.timeout_seconds = timeout_seconds
        self.auth_required = auth_required
        self.api_key_env_var = api_key_env_var
        
        # Runtime tracking fields
        self.health = "UNKNOWN"
        self.readiness = "NOT_READY"
        self.last_dispatch_ts: Optional[str] = None
        self.failure_count = 0
        self.success_count = 0

    def check_readiness(self, env: Dict[str, str]) -> str:
        if self.auth_required and self.api_key_env_var:
            if not env.get(self.api_key_env_var):
                self.readiness = "NOT_READY"
                self.health = "UNKNOWN"
                return self.readiness
        self.readiness = "READY"
        self.health = "ACTIVE"
        return self.readiness

    def to_json(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "name": self.name,
            "egress_class": self.egress_class.value,
            "capabilities": [c.value for c in self.capabilities],
            "cost_model": {
                "input_cost_per_1m": self.input_cost_per_1m,
                "output_cost_per_1m": self.output_cost_per_1m
            },
            "context_limit": self.context_limit,
            "timeout_seconds": self.timeout_seconds,
            "auth_required": self.auth_required,
            "api_key_env_var": self.api_key_env_var,
            "health": self.health,
            "readiness": self.readiness,
            "last_dispatch_ts": self.last_dispatch_ts,
            "failure_rate": self.failure_rate()
        }

    def failure_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return round(self.failure_count / total, 3)

class AdapterRegistry:
    def __init__(self):
        self.adapters = {
            "grok": AdapterRecord(
                adapter_id="grok",
                name="xAI Grok CLI",
                egress_class=EgressClass.EXTERNAL_FRONTIER,
                capabilities=[AdapterCapability.TEXT, AdapterCapability.REASONING],
                input_cost_per_1m=2.00,
                output_cost_per_1m=10.00,
                context_limit=131072,
                timeout_seconds=120,
                auth_required=True,
                api_key_env_var="XAI_API_KEY"
            ),
            "gemini": AdapterRecord(
                adapter_id="gemini",
                name="Google Gemini CLI",
                egress_class=EgressClass.EXTERNAL_FRONTIER,
                capabilities=[AdapterCapability.TEXT, AdapterCapability.VISION, AdapterCapability.TOOLS],
                input_cost_per_1m=0.15,
                output_cost_per_1m=0.60,
                context_limit=1048576,
                timeout_seconds=180,
                auth_required=True,
                api_key_env_var="GEMINI_API_KEY"
            ),
            "claude": AdapterRecord(
                adapter_id="claude",
                name="Anthropic Claude CLI",
                egress_class=EgressClass.EXTERNAL_FRONTIER,
                capabilities=[AdapterCapability.TEXT, AdapterCapability.REASONING, AdapterCapability.TOOLS],
                input_cost_per_1m=3.00,
                output_cost_per_1m=15.00,
                context_limit=200000,
                timeout_seconds=240,
                auth_required=True,
                api_key_env_var="ANTHROPIC_API_KEY"
            ),
            "openai": AdapterRecord(
                adapter_id="openai",
                name="ChatGPT API",
                egress_class=EgressClass.EXTERNAL_FRONTIER,
                capabilities=[AdapterCapability.TEXT, AdapterCapability.TOOLS],
                input_cost_per_1m=2.50,
                output_cost_per_1m=10.00,
                context_limit=128000,
                timeout_seconds=120,
                auth_required=True,
                api_key_env_var="OPENAI_API_KEY"
            ),
            "ollama": AdapterRecord(
                adapter_id="ollama",
                name="Local Ollama Gateway",
                egress_class=EgressClass.LOCAL_ONLY,
                capabilities=[AdapterCapability.TEXT, AdapterCapability.TOOLS],
                input_cost_per_1m=0.0,
                output_cost_per_1m=0.0,
                context_limit=8192,
                timeout_seconds=120,
                auth_required=False
            ),
            "lm_studio": AdapterRecord(
                adapter_id="lm_studio",
                name="Local LM Studio Gateway",
                egress_class=EgressClass.LOCAL_ONLY,
                capabilities=[AdapterCapability.TEXT],
                input_cost_per_1m=0.0,
                output_cost_per_1m=0.0,
                context_limit=8192,
                timeout_seconds=120,
                auth_required=False
            ),
            "ag_ide_relay": AdapterRecord(
                adapter_id="ag_ide_relay",
                name="AG IDE Relay Bridge",
                egress_class=EgressClass.LOCAL_ONLY,
                capabilities=[AdapterCapability.TEXT, AdapterCapability.TOOLS],
                input_cost_per_1m=0.0,
                output_cost_per_1m=0.0,
                context_limit=65536,
                timeout_seconds=300,
                auth_required=False
            )
        }

    def check_all_readiness(self, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        env_map = env or dict(os.environ)
        results = {}
        for aid, rec in self.adapters.items():
            rec.check_readiness(env_map)
            results[aid] = rec.to_json()
        return results
