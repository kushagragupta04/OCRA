from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.execution import Execution
from app.schemas.action import ExecutionInfo

router = APIRouter(prefix="/api/executions", tags=["Executions"])


@router.get("", response_model=List[ExecutionInfo])
async def list_executions(db: AsyncSession = Depends(get_db)):
    """List all Jira execution attempts, successes, and retry states."""
    stmt = select(Execution).order_by(Execution.executed_at.desc())
    execs = (await db.execute(stmt)).scalars().all()
    return [ExecutionInfo.model_validate(e) for e in execs]


@router.get("/{execution_id}", response_model=ExecutionInfo)
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch detail for a specific Jira execution event."""
    stmt = select(Execution).where(Execution.id == execution_id)
    exec_record = (await db.execute(stmt)).scalars().first()
    if not exec_record:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionInfo.model_validate(exec_record)
