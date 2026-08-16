from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class MergeDecisionORM(Base):
    __tablename__ = "merge_decisions"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("sections.canon_id"), index=True)
    lead_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    retained_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    merge_rule: Mapped[str] = mapped_column(String, default="rule_1")
    merge_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    merge_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
