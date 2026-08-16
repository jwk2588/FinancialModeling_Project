from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class MergeStatusRead(BaseModel):
    project_id: str; total_sections: int; v54_lead_count: int; v52_retained_count: int
    hybrid_count: int; pending_count: int; merge_ready_count: int
    warnings: List[str] = Field(default_factory=list)

class MergeOutlineRead(BaseModel):
    project_id: str
    sections: List[dict] = Field(default_factory=list)
    toc: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class SectionMergeResult(BaseModel):
    section_id: str; section_code: str; title: str; heading_level: int
    merged_text: Optional[str] = None; audience_mode: str; status: str
    warnings: List[str] = Field(default_factory=list)

class MasterBriefDraft(BaseModel):
    project_id: str; title: str; audience_mode: str
    toc: List[str] = Field(default_factory=list)
    sections: List[SectionMergeResult] = Field(default_factory=list)
    total_word_count: int = 0; status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
