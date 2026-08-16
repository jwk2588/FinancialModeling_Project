from pydantic import BaseModel, Field
from typing import List, Optional

class DashboardStats(BaseModel):
    project_id: str; project_title: str; source_count: int = 0
    chunk_count: int = 0; anchor_count: int = 0; section_count: int = 0
    bridge_count: int = 0; protocol_run_count: int = 0; artifact_count: int = 0
    merge_ready_sections: int = 0; pending_sections: int = 0

class SourceLaneSummary(BaseModel):
    lane: str; count: int; priority_breakdown: dict = Field(default_factory=dict)

class BridgeSummary(BaseModel):
    bridge_id: str; source_domain: str; target_domain: str
    bridge_reason: str; confidence_score: float; recommended_agent: str

class DashboardRead(BaseModel):
    stats: DashboardStats
    source_lanes: List[SourceLaneSummary] = Field(default_factory=list)
    top_bridges: List[BridgeSummary] = Field(default_factory=list)
    section_status: dict = Field(default_factory=dict)
    recent_protocol_runs: List[dict] = Field(default_factory=list)
