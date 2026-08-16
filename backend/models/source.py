from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class SourceORM(Base):
    __tablename__ = "sources"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String)
    source_lane: Mapped[str] = mapped_column(String, default="unknown")
    source_priority: Mapped[str] = mapped_column(String, default="secondary")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str] = mapped_column(Text, default="[]")
    provenance: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SourceChunkORM(Base):
    __tablename__ = "source_chunks"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.canon_id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    heading_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_tags: Mapped[str] = mapped_column(Text, default="[]")
    audience_flags: Mapped[str] = mapped_column(Text, default="[]")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
