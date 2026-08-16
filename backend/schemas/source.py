from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SourceCreate(BaseModel):
    project_id: str
    file_name: str
    source_type: str
    source_lane: str = "unknown"
    source_priority: str = "secondary"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    provenance: Optional[str] = None
    raw_content: Optional[str] = None

class SourceRead(BaseModel):
    canon_id: str
    project_id: str
    file_name: str
    source_type: str
    source_lane: str
    source_priority: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    provenance: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class SourceChunkRead(BaseModel):
    canon_id: str
    source_id: str
    chunk_index: int
    page_ref: Optional[str] = None
    heading_ref: Optional[str] = None
    raw_text: str
    normalized_text: Optional[str] = None
    domain_tags: List[str] = Field(default_factory=list)
    audience_flags: List[str] = Field(default_factory=list)
    confidence_score: float
    created_at: datetime
    model_config = {"from_attributes": True}
