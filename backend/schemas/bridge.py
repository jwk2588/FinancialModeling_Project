from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BridgeDetectRequest(BaseModel):
    project_id: str
    source_domain: str
    target_domain: str
    source_node_label: str
    target_node_label: str
    bridge_reason: str
    anchor_refs: List[str] = Field(default_factory=list)
    confidence_score: float = 0.8

class BridgeRead(BaseModel):
    canon_id: str
    project_id: str
    source_domain: str
    target_domain: str
    source_node_label: str
    target_node_label: str
    bridge_reason: str
    bridge_type: str
    recommended_agent: str
    confidence_score: float
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}

class BridgeGraphNode(BaseModel):
    id: str; label: str; type: str; title: str; domain: str

class BridgeGraphEdge(BaseModel):
    id: str; source: str; target: str; bridge_reason: str
    confidence_score: float; recommended_agent: str

class DomainGraphPayload(BaseModel):
    project_id: str
    nodes: List[BridgeGraphNode] = Field(default_factory=list)
    edges: List[BridgeGraphEdge] = Field(default_factory=list)
