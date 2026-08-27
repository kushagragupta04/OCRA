from sqlalchemy import Column, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String(100), nullable=False, default="system")
    action_id = Column(String(36), nullable=True, index=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False)  # TRANSCRIPT_INGESTED, EXTRACTION_COMPLETED, POLICY_EVALUATED, AUTO_EXECUTED, ACTION_APPROVED, ACTION_REJECTED, EXECUTION_SUCCESS, EXECUTION_FAILED, ROLLBACK_INITIATED
    before_state = Column(Text, nullable=True)  # JSON representation
    after_state = Column(Text, nullable=True)   # JSON representation
    timestamp = Column(DateTime, nullable=False, default=func.now())

    meeting = relationship("Meeting", back_populates="audit_events")
