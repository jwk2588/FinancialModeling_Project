from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class AgentRunRequest(BaseModel):
    project_id: str
    agent_name: str = ""
    task: str
    input_refs: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    audience_mode: str = "outside_counsel"

class AgentRunResult(BaseModel):
    agent_name: str
    task: str
    status: str = "success"
    output_type: str
    output: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    protocol_run_id: Optional[str] = None

class AgentStatusRead(BaseModel):
    wolf: str = "ready"; tiger: str = "ready"; master_nexus: str = "ready"; active_runs: int = 0
