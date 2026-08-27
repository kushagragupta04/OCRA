from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_id = Column(String(100), nullable=False, default="speaker_0")
    speaker_name = Column(String(100), nullable=False, default="Unknown Speaker")
    start_ms = Column(Integer, nullable=False, default=0)
    end_ms = Column(Integer, nullable=False, default=0)
    text = Column(String(4000), nullable=False)

    meeting = relationship("Meeting", back_populates="segments")
