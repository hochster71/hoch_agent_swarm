from __future__ import annotations

import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator

class AuthenticationContext(BaseModel):
    method: str = Field(..., description="oauth | app_attestation | local_session")
    assurance_level: str = Field(..., description="LOW | MODERATE | HIGH")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        allowed = {"oauth", "app_attestation", "local_session"}
        if v.lower() not in allowed:
            raise ValueError(f"Authentication method must be one of {allowed}")
        return v.lower()

    @field_validator("assurance_level")
    @classmethod
    def validate_assurance(cls, v: str) -> str:
        allowed = {"LOW", "MODERATE", "HIGH"}
        if v.upper() not in allowed:
            raise ValueError(f"Assurance level must be one of {allowed}")
        return v.upper()

class ConfirmationContext(BaseModel):
    required: bool = Field(default=False)
    challenge_id: Optional[str] = Field(default=None)
    confirmed: bool = Field(default=False)

class VoiceRequestEnvelope(BaseModel):
    request_id: str = Field(..., pattern=r"^VOICE-REQ-[A-Za-z0-9_\-]+$")
    provider: str = Field(..., description="ALEXA | SIRI | WEB")
    device_id_hash: str = Field(..., pattern=r"^sha256:[a-f0-9]{64}$")
    actor_id: str = Field(..., description="founder identity reference")
    session_id: str = Field(..., description="provider-neutral session identifier")
    timestamp: str = Field(..., description="RFC3339 UTC timestamp")
    intent: str = Field(..., description="Intent identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    utterance_redacted: str = Field(..., description="sanitized spoken text")
    authentication_context: AuthenticationContext
    confirmation: ConfirmationContext
    nonce: str = Field(..., description="Anti-replay nonce")
    signature: str = Field(..., description="Request cryptographic signature")
    schema_version: str = Field(default="1.0.0")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"ALEXA", "SIRI", "WEB"}
        if v.upper() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v.upper()

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        # Simple ISO8601 / RFC3339 validator regex
        rfc3339_regex = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
        if not re.match(rfc3339_regex, v):
            raise ValueError("Timestamp must match RFC3339 UTC format (e.g. YYYY-MM-DDTHH:MM:SSZ)")
        return v
