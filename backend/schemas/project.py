from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    provenance: Optional[str] = None

class ProjectRead(BaseModel):
    canon_id: str
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    provenance: Optional[str] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ProjectSummary(BaseModel):
    canon_id: str
    title: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}
