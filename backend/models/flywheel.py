from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from backend.models.base import Base

class FlywheelORM(Base):
    __tablename__ = "flywheels"
    canon_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.canon_id"), index=True)
    flywheel_name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    current_cycle: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
