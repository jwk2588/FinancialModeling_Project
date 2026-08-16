from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class EvidenceAnchorORM(Base):
    __tablename__ = "evidence_anchors"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    source_chunk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    normalized_fact: Mapped[str] = mapped_column(Text, nullable=False)
    raw_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_type: Mapped[str] = mapped_column(String, default="direct_proof")
    domain_tags: Mapped[str] = mapped_column(Text, default="[]")
    audience_flags: Mapped[str] = mapped_column(Text, default="[]")
    ev_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.9)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SectionSupportLinkORM(Base):
    __tablename__ = "section_support_links"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("sections.canon_id"), index=True)
    evidence_anchor_id: Mapped[str] = mapped_column(String, ForeignKey("evidence_anchors.canon_id"), index=True)
    support_role: Mapped[str] = mapped_column(String, default="primary_support")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
