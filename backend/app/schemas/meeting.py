from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class SegmentInput(BaseModel):
    id: Optional[str] = None
    speaker_id: Optional[str] = "speaker_0"
    speaker_name: str = "Unknown"
    start_ms: int = 0
    end_ms: int = 0
    text: str


class TranscriptIngestRequest(BaseModel):
    title: Optional[str] = "Engineering Sync"
    provider: Optional[str] = "manual"
    external_id: Optional[str] = None
    segments: Optional[List[SegmentInput]] = None
    raw_text: Optional[str] = None
    project_key: Optional[str] = "PAY"


class LiveChunkRequest(BaseModel):
    speaker_id: Optional[str] = None
    speaker_name: str = "Rahul"
    start_ms: int = 0
    end_ms: int = 0
    text: str
    is_final: bool = False


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    speaker_id: str
    speaker_name: str
    start_ms: int
    end_ms: int
    text: str


class MeetingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    provider: str
    external_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    transcript_hash: Optional[str] = None
    status: str
    segment_count: Optional[int] = 0
    action_count: Optional[int] = 0
    segments: Optional[List[SegmentResponse]] = []
