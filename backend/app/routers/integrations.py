from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from app.database import get_db
from app.models.jira_config import JiraConfig
from app.schemas.jira import JiraProject, JiraConfigUpdate, JiraConfigResponse, JiraUser
from app.adapters import (
    get_jira_adapter,
    get_sandbox_adapter,
    get_github_adapter,
    get_calendar_adapter,
)
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


# ===================================================================== #
# GitHub Issues integration (blueprint Section 15.1)                     #
# ===================================================================== #
github_router = APIRouter(prefix="/api/integrations/github", tags=["Integrations"])


class GithubConnectRequest(BaseModel):
    token: Optional[str] = None
    default_repo: Optional[str] = None  # "owner/repo"


@github_router.post("/connect")
async def connect_github(payload: GithubConnectRequest):
    """
    Start/complete the GitHub connection flow.

    Mirrors the Jira connection endpoint's shape. A real deployment would run the
    GitHub OAuth flow and persist the token server-side; here we accept a PAT /
    fine-grained token (or fall back to the credential-free mock sandbox).
    """
    if payload.token:
        settings.GITHUB_TOKEN = payload.token
        settings.USE_MOCK_GITHUB = False
    if payload.default_repo:
        settings.GITHUB_DEFAULT_REPO = payload.default_repo

    adapter = get_github_adapter()
    mode = "mock" if adapter.__class__.__name__.endswith("MockSandboxAdapter") else "live"
    repos: List[str] = []
    try:
        repos = [r.full_name for r in await adapter.get_repos()]
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"GitHub connection failed: {e}")

    return {
        "connected": True,
        "provider": "github",
        "mode": mode,
        "default_repo": settings.GITHUB_DEFAULT_REPO,
        "repos_available": repos,
    }


@github_router.get("/repos")
async def list_github_repos():
    """List repositories accessible to the configured GitHub connector."""
    adapter = get_github_adapter()
    return {"repos": [r.model_dump() for r in await adapter.get_repos()]}


# ===================================================================== #
# Google Calendar integration (blueprint Section 15.1)                   #
# ===================================================================== #
calendar_router = APIRouter(prefix="/api/integrations/calendar", tags=["Integrations"])


class CalendarConnectRequest(BaseModel):
    access_token: Optional[str] = None   # OAuth2 access token (3LO — same pattern as Jira)
    calendar_id: Optional[str] = None


@calendar_router.post("/connect")
async def connect_calendar(payload: CalendarConnectRequest):
    """
    Start/complete the Google Calendar connection flow.

    Uses the same OAuth2 3LO pattern as Jira (see the Jira integration flow):
    the browser completes consent, the backend exchanges the code for an access
    token and stores it server-side. Here we accept the token directly or fall
    back to the credential-free mock.
    """
    if payload.access_token:
        settings.GOOGLE_OAUTH_ACCESS_TOKEN = payload.access_token
        settings.USE_MOCK_CALENDAR = False
    if payload.calendar_id:
        settings.GOOGLE_CALENDAR_ID = payload.calendar_id

    adapter = get_calendar_adapter()
    mode = "mock" if adapter.__class__.__name__.endswith("MockAdapter") else "live"
    return {
        "connected": True,
        "provider": "google_calendar",
        "mode": mode,
        "calendar_id": settings.GOOGLE_CALENDAR_ID,
    }
