from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class BridgeORM(Base):
    __tablename__ = "bridges"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    source_domain: Mapped[str] = mapped_column(String)
    target_domain: Mapped[str] = mapped_column(String)
    source_node_label: Mapped[str] = mapped_column(String)
    target_node_label: Mapped[str] = mapped_column(String)
    bridge_reason: Mapped[str] = mapped_column(Text)
    bridge_type: Mapped[str] = mapped_column(String, default="cross_domain")
    recommended_agent: Mapped[str] = mapped_column(String, default="tiger")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class BridgeAnchorLinkORM(Base):
    __tablename__ = "bridge_anchor_links"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    bridge_id: Mapped[str] = mapped_column(String, ForeignKey("bridges.canon_id"), index=True)
    evidence_anchor_id: Mapped[str] = mapped_column(String, ForeignKey("evidence_anchors.canon_id"), index=True)
    link_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
