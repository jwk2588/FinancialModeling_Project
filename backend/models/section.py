from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class SectionORM(Base):
    __tablename__ = "sections"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    section_code: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    heading_level: Mapped[int] = mapped_column(Integer, default=1)
    parent_section_id: Mapped[str | None] = mapped_column(String, nullable=True)
    drafting_mode: Mapped[str] = mapped_column(String, default="pending")
    bunker_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    engine_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SectionVersionORM(Base):
    __tablename__ = "section_versions"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("sections.canon_id"), index=True)
    version_label: Mapped[str] = mapped_column(String)
    source_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    ownership_mode: Mapped[str] = mapped_column(String, default="v52")
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False)
    is_retained_depth: Mapped[bool] = mapped_column(Boolean, default=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_mode: Mapped[str] = mapped_column(String, default="outside_counsel")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
