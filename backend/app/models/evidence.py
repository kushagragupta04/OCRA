from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(String(36), nullable=False)
    start_ms = Column(Integer, nullable=False, default=0)
    end_ms = Column(Integer, nullable=False, default=0)
    evidence_text = Column(Text, nullable=False)

    action = relationship("Action", back_populates="evidence")
