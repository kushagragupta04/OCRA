from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    required = Column(Boolean, nullable=False, default=True)
    reviewer = Column(String(100), nullable=True)
    decision = Column(String(30), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)

    action = relationship("Action", back_populates="approval")
