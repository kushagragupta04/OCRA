from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="Untitled Engineering Meeting")
    provider = Column(String(50), nullable=False, default="manual")
    external_id = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    transcript_hash = Column(String(64), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS, PROCESSING, COMPLETED, FAILED

    segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan", lazy="selectin", order_by="TranscriptSegment.start_ms")
    actions = relationship("Action", back_populates="meeting", cascade="all, delete-orphan", lazy="selectin")
    audit_events = relationship("AuditEvent", back_populates="meeting", cascade="all, delete-orphan", lazy="selectin")
