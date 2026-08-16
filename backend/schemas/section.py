from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SectionCreate(BaseModel):
    project_id: str
    section_code: str
    title: str
    heading_level: int = 1
    parent_section_id: Optional[str] = None
    drafting_mode: str = "pending"
    bunker_flag: bool = False
    engine_flag: bool = False
    display_order: int = 0

class SectionRead(BaseModel):
    canon_id: str
    project_id: str
    section_code: str
    title: str
    heading_level: int
    parent_section_id: Optional[str] = None
    drafting_mode: str
    bunker_flag: bool
    engine_flag: bool
    display_order: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class SectionVersionCreate(BaseModel):
    section_id: str = ""
    version_label: str
    source_ref: Optional[str] = None
    ownership_mode: str = "v52"
    is_lead: bool = False
    is_retained_depth: bool = False
    supersedes_version_id: Optional[str] = None
    text_body: Optional[str] = None
    audience_mode: str = "outside_counsel"

class SectionVersionRead(BaseModel):
    canon_id: str
    section_id: str
    version_label: str
    source_ref: Optional[str] = None
    ownership_mode: str
    is_lead: bool
    is_retained_depth: bool
    supersedes_version_id: Optional[str] = None
    text_body: Optional[str] = None
    audience_mode: str
    created_at: datetime
    model_config = {"from_attributes": True}

class MergeCard(BaseModel):
    section_id: str
    section_code: str
    title: str
    heading_level: int
    drafting_mode: str
    bunker_flag: bool
    lead_version: Optional[SectionVersionRead] = None
    retained_versions: List[SectionVersionRead] = Field(default_factory=list)
    support_anchor_count: int = 0
    merge_ready: bool = False
    warnings: List[str] = Field(default_factory=list)
