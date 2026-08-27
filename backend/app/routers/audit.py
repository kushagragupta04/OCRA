from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventResponse

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


@router.get("", response_model=List[AuditEventResponse])
async def list_audit_events(
    meeting_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve immutable audit event trail."""
    stmt = select(AuditEvent)
    if meeting_id:
        stmt = stmt.where(AuditEvent.meeting_id == meeting_id)
    stmt = stmt.order_by(AuditEvent.timestamp.desc()).limit(limit)

    events = (await db.execute(stmt)).scalars().all()
    return [AuditEventResponse.model_validate(ev) for ev in events]
