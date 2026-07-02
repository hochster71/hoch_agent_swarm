from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class PromptIngestRequest(BaseModel):
    source: str
    raw_text: str

class AgRunIngestRequest(BaseModel):
    agent_role: str
    task_description: str
    status: str
    result: Optional[str] = None
    raw_prompt: Optional[str] = None

class SynthesizeRequest(BaseModel):
    force_refresh: Optional[bool] = False
