from sqlalchemy import Column, String, Boolean, Float, Text, DateTime, func
import uuid
from app.database import Base


class JiraConfig(Base):
    __tablename__ = "jira_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_key = Column(String(20), nullable=False, unique=True, index=True)
    project_name = Column(String(100), nullable=False, default="Payments & Core")
    auto_execute_enabled = Column(Boolean, nullable=False, default=True)
    min_confidence_threshold = Column(Float, nullable=False, default=0.80)
    kill_switch_active = Column(Boolean, nullable=False, default=False)
    allowed_transitions = Column(Text, nullable=False, default='["To Do", "In Progress", "In Review", "Done"]')
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
