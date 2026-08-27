from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor: str
    action_id: Optional[str] = None
    meeting_id: Optional[str] = None
    event_type: str
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    timestamp: datetime
