from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class OutputArtifactORM(Base):
    __tablename__ = "output_artifacts"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    output_kind: Mapped[str] = mapped_column(String)
    audience_mode: Mapped[str] = mapped_column(String, default="outside_counsel")
    title: Mapped[str] = mapped_column(String)
    section_refs: Mapped[str] = mapped_column(Text, default="[]")
    artifact_path: Mapped[str | None] = mapped_column(String, nullable=True)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
