from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ExportRequest(BaseModel):
    project_id: str
    audience_mode: str = "outside_counsel"
    include_toc: bool = True
    include_appendices: bool = True
    section_filter: List[str] = Field(default_factory=list)

class ExportArtifactRead(BaseModel):
    canon_id: str; project_id: str; output_kind: str; audience_mode: str
    title: str; section_refs: List[str] = Field(default_factory=list)
    artifact_path: Optional[str] = None; status: str; created_at: datetime
    model_config = {"from_attributes": True}

class ExportPreview(BaseModel):
    project_id: str; audience_mode: str
    heading_tree: List[dict] = Field(default_factory=list)
    toc_lines: List[str] = Field(default_factory=list)
    appendix_list: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    estimated_pages: int = 0
