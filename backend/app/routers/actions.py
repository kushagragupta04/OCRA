from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db
from app.models.action import Action
from app.models.approval import Approval
from app.models.evidence import Evidence
from app.models.execution import Execution
from app.schemas.action import (
    ActionResponse,
    ApproveRejectRequest,
    EvidenceRef,
    ConflictDetails,
    ApprovalInfo,
    ExecutionInfo
)
from app.schemas.execution import ExecutionPlanResponse
from app.services.execution_service import ExecutionService
from app.services.audit_service import AuditService

router = APIRouter(tags=["Actions & Approvals"])


def _format_action_response(a: Action) -> ActionResponse:
    conflict_info = None
    if a.conflict_payload:
        try:
            parsed = json.loads(a.conflict_payload)
            conflict_info = ConflictDetails(**parsed)
        except Exception:
            pass

    return ActionResponse(
        id=a.id,
        meeting_id=a.meeting_id,
        action_type=a.action_type,
        summary=a.summary,
        description=a.description,
        target_issue_key=a.target_issue_key,
        project_key=a.project_key,
        issue_type=a.issue_type,
        owner_account_id=a.owner_account_id,
        owner_name=a.owner_name,
        due_at=a.due_at,
        priority=a.priority,
        confidence=a.confidence,
        risk=a.risk,
        status=a.status,
        reason=a.reason,
        conflict_payload=a.conflict_payload,
        transition_name=a.transition_name,
        created_at=a.created_at,
        evidence=[EvidenceRef.model_validate(ev) for ev in a.evidence],
        executions=[ExecutionInfo.model_validate(ex) for ex in a.executions],
        approval=ApprovalInfo.model_validate(a.approval) if a.approval else None,
        conflict_info=conflict_info
    )


@router.get("/api/meetings/{meeting_id}/actions", response_model=ExecutionPlanResponse)
async def get_meeting_actions(meeting_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch structured execution plan for a meeting grouped by category."""
    stmt = (
        select(Action)
        .where(Action.meeting_id == meeting_id)
        .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
    )
    actions = (await db.execute(stmt)).scalars().all()

    auto_executable = []
    requires_approval = []
    conflicts = []
    executed = []

    for a in actions:
        resp = _format_action_response(a)
        if a.status in ["COMPLETED", "AUTO_EXECUTED"]:
            executed.append(resp)
        elif a.action_type == "CONFLICT" or a.conflict_payload:
            conflicts.append(resp)
        elif a.status == "REQUIRES_APPROVAL":
            requires_approval.append(resp)
        else:
            auto_executable.append(resp)

    return ExecutionPlanResponse(
        meeting_id=meeting_id,
        total_actions=len(actions),
        auto_executable=auto_executable,
        requires_approval=requires_approval,
        conflicts=conflicts,
        executed=executed,
        policy_summary={
            "total": len(actions),
            "executed_count": len(executed),
            "pending_approval_count": len(requires_approval) + len(conflicts),
            "conflicts_count": len(conflicts)
        }
    )


@router.get("/api/approvals/pending", response_model=List[ActionResponse])
async def list_pending_approvals(db: AsyncSession = Depends(get_db)):
    """List all actions across all meetings currently requiring approval."""
    stmt = (
        select(Action)
        .where(Action.status == "REQUIRES_APPROVAL")
        .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
        .order_by(Action.created_at.desc())
    )
    actions = (await db.execute(stmt)).scalars().all()
    return [_format_action_response(a) for a in actions]


@router.post("/api/actions/{action_id}/approve", response_model=ActionResponse)
async def approve_action(
    action_id: str,
    payload: ApproveRejectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Approve an action and trigger idempotent execution in Jira."""
    stmt = (
        select(Action)
        .where(Action.id == action_id)
        .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
    )
    action = (await db.execute(stmt)).scalars().first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if not action.approval:
        action.approval = Approval(action_id=action.id, required=True)
        db.add(action.approval)

    action.approval.decision = "APPROVED"
    action.approval.reviewer = payload.reviewer or "Engineering Lead"
    action.approval.comment = payload.comment
    action.approval.decided_at = datetime.utcnow()
    action.status = "APPROVED"
    await db.commit()

    # Log approval audit
    await AuditService.log_event(
        db=db,
        actor=f"user:{payload.reviewer or 'Lead'}",
        event_type="ACTION_APPROVED",
        meeting_id=action.meeting_id,
        action_id=action.id,
        after_state={"decision": "APPROVED", "comment": payload.comment}
    )

    # Execute in Jira
    await ExecutionService.execute_action(db, action.id, actor=f"user:{payload.reviewer or 'Lead'}")
    
    # Reload
    stmt_reload = (
        select(Action)
        .where(Action.id == action_id)
        .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
    )
    reloaded = (await db.execute(stmt_reload)).scalars().first()
    return _format_action_response(reloaded)


@router.post("/api/actions/{action_id}/reject", response_model=ActionResponse)
async def reject_action(
    action_id: str,
    payload: ApproveRejectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reject a proposed action with explanation."""
    stmt = (
        select(Action)
        .where(Action.id == action_id)
        .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
    )
    action = (await db.execute(stmt)).scalars().first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if not action.approval:
        action.approval = Approval(action_id=action.id, required=True)
        db.add(action.approval)

    action.approval.decision = "REJECTED"
    action.approval.reviewer = payload.reviewer or "Engineering Lead"
    action.approval.comment = payload.comment
    action.approval.decided_at = datetime.utcnow()
    action.status = "REJECTED"
    await db.commit()

    await AuditService.log_event(
        db=db,
        actor=f"user:{payload.reviewer or 'Lead'}",
        event_type="ACTION_REJECTED",
        meeting_id=action.meeting_id,
        action_id=action.id,
        after_state={"decision": "REJECTED", "comment": payload.comment}
    )

    return _format_action_response(action)


@router.post("/api/actions/{action_id}/execute", response_model=ActionResponse)
async def execute_action(action_id: str, db: AsyncSession = Depends(get_db)):
    """Manually execute an approved or proposed action."""
    await ExecutionService.execute_action(db, action_id, actor="user:manual_trigger")
    stmt = (
        select(Action)
        .where(Action.id == action_id)
        .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
    )
    action = (await db.execute(stmt)).scalars().first()
    return _format_action_response(action)
