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
    # Which connector handled this execution (blueprint Section 15). Defaults to
    # "jira" so legacy rows keep their meaning.
    target_connector = Column(String(30), nullable=False, default="jira", server_default="jira")
    # Generic external references. ``jira_issue_key`` / ``jira_response_id`` are
    # retained (and reused for non-Jira connectors: issue number / event id) so
    # existing readers keep working; ``external_url`` is the openable link.
    jira_issue_key = Column(String(50), nullable=True)
    jira_response_id = Column(String(100), nullable=True)
    external_url = Column(String(500), nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    executed_at = Column(DateTime, nullable=False, default=func.now())

    action = relationship("Action", back_populates="executions")
