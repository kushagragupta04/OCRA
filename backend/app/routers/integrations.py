from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.database import get_db
from app.models.jira_config import JiraConfig
from app.schemas.jira import JiraProject, JiraConfigUpdate, JiraConfigResponse, JiraUser
from app.adapters import get_jira_adapter, get_sandbox_adapter
from app.config import settings

router = APIRouter(prefix="/api/integrations/jira", tags=["Integrations"])


@router.get("/projects", response_model=List[JiraProject])
async def get_projects():
    """Fetch accessible projects from configured Jira adapter."""
    adapter = get_jira_adapter()
    return await adapter.get_projects()


@router.get("/users", response_model=List[JiraUser])
async def get_users(query: str = ""):
    """Fetch accessible Jira users for assignment and resolution."""
    adapter = get_jira_adapter()
    return await adapter.get_users(query)


@router.get("/settings", response_model=JiraConfigResponse)
async def get_jira_settings(project_key: str = "PAY", db: AsyncSession = Depends(get_db)):
    """Fetch project policy configuration and autonomy controls."""
    stmt = select(JiraConfig).where(JiraConfig.project_key == project_key)
    config = (await db.execute(stmt)).scalars().first()
    
    if not config:
        config = JiraConfig(
            project_key=project_key,
            project_name="Payments & Checkout",
            auto_execute_enabled=settings.AUTO_EXECUTE_ENABLED,
            min_confidence_threshold=settings.MIN_CONFIDENCE_THRESHOLD,
            kill_switch_active=settings.KILL_SWITCH_ACTIVE
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    import json
    transitions = json.loads(config.allowed_transitions) if isinstance(config.allowed_transitions, str) else ["To Do", "In Progress", "In Review", "Done"]
    return JiraConfigResponse(
        id=config.id,
        project_key=config.project_key,
        project_name=config.project_name,
        auto_execute_enabled=config.auto_execute_enabled,
        min_confidence_threshold=config.min_confidence_threshold,
        kill_switch_active=config.kill_switch_active,
        allowed_transitions=transitions,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.post("/settings", response_model=JiraConfigResponse)
async def update_jira_settings(payload: JiraConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Update autonomy policy, confidence thresholds, or trigger master kill-switch."""
    project_key = payload.project_key or "PAY"
    stmt = select(JiraConfig).where(JiraConfig.project_key == project_key)
    config = (await db.execute(stmt)).scalars().first()

    if not config:
        config = JiraConfig(project_key=project_key)
        db.add(config)

    if payload.auto_execute_enabled is not None:
        config.auto_execute_enabled = payload.auto_execute_enabled
    if payload.min_confidence_threshold is not None:
        config.min_confidence_threshold = payload.min_confidence_threshold
    if payload.kill_switch_active is not None:
        config.kill_switch_active = payload.kill_switch_active
    if payload.allowed_transitions is not None:
        import json
        config.allowed_transitions = json.dumps(payload.allowed_transitions)

    await db.commit()
    await db.refresh(config)

    import json
    transitions = json.loads(config.allowed_transitions) if isinstance(config.allowed_transitions, str) else ["To Do", "In Progress", "In Review", "Done"]
    return JiraConfigResponse(
        id=config.id,
        project_key=config.project_key,
        project_name=config.project_name,
        auto_execute_enabled=config.auto_execute_enabled,
        min_confidence_threshold=config.min_confidence_threshold,
        kill_switch_active=config.kill_switch_active,
        allowed_transitions=transitions,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/sandbox/issues")
async def get_sandbox_issues():
    """Retrieve full live issue board from Jira Mock Sandbox for real-time inspection."""
    adapter = get_jira_adapter()
    issues = await adapter.search_issues("ORDER BY created DESC", limit=100)
    return {"issues": issues}


@router.post("/sandbox/reset")
async def reset_sandbox():
    """Reset Jira Sandbox to clean initial state."""
    sandbox = get_sandbox_adapter()
    sandbox.reset()
    return {"message": "Jira Mock Sandbox successfully reset to initial backlog state."}
