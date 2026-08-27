from sqlalchemy import Column, String, Float, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(30), nullable=False)  # CREATE, UPDATE, ASSIGN, COMMENT, SHIFT_DEADLINE, TRANSITION, CONFLICT, NO_ACTION
    summary = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    target_issue_key = Column(String(50), nullable=True, index=True)
    project_key = Column(String(20), nullable=False, default="PAY")
    issue_type = Column(String(50), nullable=False, default="Task")
    owner_account_id = Column(String(100), nullable=True)
    owner_name = Column(String(100), nullable=True)
    due_at = Column(String(50), nullable=True)
    priority = Column(String(30), nullable=True, default="Medium")
    confidence = Column(Float, nullable=False, default=1.0)
    risk = Column(String(20), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH
    status = Column(String(30), nullable=False, default="PROPOSED")  # PROPOSED, AUTO_EXECUTED, REQUIRES_APPROVAL, APPROVED, REJECTED, EXECUTING, COMPLETED, FAILED
    reason = Column(Text, nullable=False)
    conflict_payload = Column(Text, nullable=True)  # JSON string for contradiction / scope diff
    transition_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    meeting = relationship("Meeting", back_populates="actions")
    evidence = relationship("Evidence", back_populates="action", cascade="all, delete-orphan", lazy="selectin")
    executions = relationship("Execution", back_populates="action", cascade="all, delete-orphan", lazy="selectin")
    approval = relationship("Approval", back_populates="action", uselist=False, cascade="all, delete-orphan", lazy="selectin")
