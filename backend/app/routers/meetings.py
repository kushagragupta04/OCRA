from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import uuid
import json

from app.database import get_db
from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment
from app.models.action import Action
from app.models.approval import Approval
from app.schemas.meeting import (
    MeetingResponse,
    TranscriptIngestRequest,
    LiveChunkRequest,
    SegmentResponse
)
from app.services.ingestion_service import IngestionService
from app.services.extraction_service import ExtractionService
from app.services.policy_engine import PolicyEngine
from app.services.execution_service import ExecutionService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])


@router.get("", response_model=List[MeetingResponse])
async def list_meetings(db: AsyncSession = Depends(get_db)):
    """List all meetings with segment and action statistics."""
    stmt = (
        select(Meeting)
        .options(selectinload(Meeting.segments), selectinload(Meeting.actions))
        .order_by(Meeting.started_at.desc())
    )
    meetings = (await db.execute(stmt)).scalars().all()
    
    res = []
    for m in meetings:
        res.append(MeetingResponse(
            id=m.id,
            title=m.title,
            provider=m.provider,
            external_id=m.external_id,
            started_at=m.started_at,
            ended_at=m.ended_at,
            transcript_hash=m.transcript_hash,
            status=m.status,
            segment_count=len(m.segments),
            action_count=len(m.actions)
        ))
    return res


@router.post("", response_model=MeetingResponse)
async def create_or_upload_meeting(
    request: TranscriptIngestRequest,
    auto_process: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a meeting transcript (structured segments or raw text).
    If auto_process=True, runs the full reasoning and execution pipeline.
    """
    meeting = await IngestionService.ingest_transcript(db, request)

    if auto_process and meeting.status != "COMPLETED":
        await _run_pipeline(db, meeting.id, request.project_key or "PAY")

    # Reload with relations
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting.id)
        .options(selectinload(Meeting.segments), selectinload(Meeting.actions))
    )
    reloaded = (await db.execute(stmt)).scalars().first()

    return MeetingResponse(
        id=reloaded.id,
        title=reloaded.title,
        provider=reloaded.provider,
        external_id=reloaded.external_id,
        started_at=reloaded.started_at,
        ended_at=reloaded.ended_at,
        transcript_hash=reloaded.transcript_hash,
        status=reloaded.status,
        segment_count=len(reloaded.segments),
        action_count=len(reloaded.actions),
        segments=[SegmentResponse.model_validate(s) for s in reloaded.segments]
    )


@router.post("/{meeting_id}/chunks")
async def append_live_chunk(
    meeting_id: str,
    chunk: LiveChunkRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Appends a live conversation segment from an ongoing meeting.
    """
    stmt = select(Meeting).where(Meeting.id == meeting_id)
    meeting = (await db.execute(stmt)).scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    seg = TranscriptSegment(
        id=str(uuid.uuid4()),
        meeting_id=meeting_id,
        speaker_id=chunk.speaker_id or f"spk_{chunk.speaker_name.lower().replace(' ', '_')}",
        speaker_name=chunk.speaker_name,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        text=chunk.text
    )
    db.add(seg)
    await db.commit()

    return {"status": "appended", "segment_id": seg.id}


@router.post("/{meeting_id}/process", response_model=MeetingResponse)
async def process_meeting(
    meeting_id: str,
    project_key: str = "PAY",
    db: AsyncSession = Depends(get_db)
):
    """
    Finalizes an in-progress or uploaded meeting and executes the full reasoning pipeline:
    Extraction -> Context Discovery -> Duplicate/Conflict Detection -> Policy Evaluation -> Execution.
    """
    stmt = select(Meeting).where(Meeting.id == meeting_id)
    meeting = (await db.execute(stmt)).scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    await _run_pipeline(db, meeting_id, project_key)

    # Reload
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(selectinload(Meeting.segments), selectinload(Meeting.actions))
    )
    reloaded = (await db.execute(stmt)).scalars().first()

    return MeetingResponse(
        id=reloaded.id,
        title=reloaded.title,
        provider=reloaded.provider,
        external_id=reloaded.external_id,
        started_at=reloaded.started_at,
        ended_at=reloaded.ended_at,
        transcript_hash=reloaded.transcript_hash,
        status=reloaded.status,
        segment_count=len(reloaded.segments),
        action_count=len(reloaded.actions),
        segments=[SegmentResponse.model_validate(s) for s in reloaded.segments]
    )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch meeting detail with full timestamped transcript segments."""
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(selectinload(Meeting.segments), selectinload(Meeting.actions))
    )
    meeting = (await db.execute(stmt)).scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        provider=meeting.provider,
        external_id=meeting.external_id,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        transcript_hash=meeting.transcript_hash,
        status=meeting.status,
        segment_count=len(meeting.segments),
        action_count=len(meeting.actions),
        segments=[SegmentResponse.model_validate(s) for s in meeting.segments]
    )


async def _run_pipeline(db: AsyncSession, meeting_id: str, project_key: str):
    """
    Internal orchestrator for the 15-step processing pipeline.
    """
    # 1. Update meeting status
    stmt = select(Meeting).where(Meeting.id == meeting_id)
    meeting = (await db.execute(stmt)).scalars().first()
    if meeting:
        meeting.status = "PROCESSING"
        meeting.ended_at = datetime.utcnow()
        await db.commit()

    # 2. Extract actions with prompt isolation and entity resolution
    extracted_actions = await ExtractionService.extract_meeting_actions(db, meeting_id, project_key)

    # 3. Policy Evaluation and Gating
    for action in extracted_actions:
        evidence_text = action.evidence[0].evidence_text if action.evidence else ""
        policy_result = await PolicyEngine.evaluate_action_policy(db, action, evidence_text)
        
        status = policy_result["status"]
        requires_approval = policy_result["approval_required"]

        # Create Approval record if required
        if requires_approval:
            action.status = "REQUIRES_APPROVAL"
            approval = Approval(
                id=str(uuid.uuid4()),
                action_id=action.id,
                required=True,
                decision="PENDING",
                comment=policy_result.get("policy_reason")
            )
            db.add(approval)
        elif status == "AUTO_EXECUTABLE":
            action.status = "AUTO_EXECUTED"
            approval = Approval(
                id=str(uuid.uuid4()),
                action_id=action.id,
                required=False,
                decision="APPROVED",
                comment="Auto-approved by Policy Engine."
            )
            db.add(approval)
            await db.commit()

            # Execute safe action immediately
            try:
                await ExecutionService.execute_action(db, action.id, actor="system:auto_executor")
            except Exception as e:
                print(f"Auto-execution failed for action {action.id}: {e}")

    # Mark meeting COMPLETED
    if meeting:
        meeting.status = "COMPLETED"
        await db.commit()
