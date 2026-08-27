from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Execution(Base):
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = Column(String(50), nullable=False)  # CREATE_ISSUE, UPDATE_ISSUE, SHIFT_DEADLINE, ADD_COMMENT, ASSIGN_USER, TRANSITION_ISSUE
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="PENDING")  # PENDING, EXECUTING, SUCCESS, FAILED
    jira_issue_key = Column(String(50), nullable=True)
    jira_response_id = Column(String(100), nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    executed_at = Column(DateTime, nullable=False, default=func.now())

    action = relationship("Action", back_populates="executions")
