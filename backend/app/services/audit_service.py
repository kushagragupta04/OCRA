from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime
import json
import uuid

from app.models.audit import AuditEvent


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        actor: str,
        event_type: str,
        meeting_id: Optional[str] = None,
        action_id: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid.uuid4()),
            actor=actor,
            meeting_id=meeting_id,
            action_id=action_id,
            event_type=event_type,
            before_state=json.dumps(before_state) if before_state else None,
            after_state=json.dumps(after_state) if after_state else None,
            timestamp=datetime.utcnow()
        )
        db.add(event)
        await db.commit()
        return event
