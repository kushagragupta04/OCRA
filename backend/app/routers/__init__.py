from app.routers.integrations import (
    router as integrations_router,
    github_router as github_integrations_router,
    calendar_router as calendar_integrations_router,
)
from app.routers.meetings import router as meetings_router
from app.routers.actions import router as actions_router
from app.routers.executions import router as executions_router
from app.routers.audit import router as audit_router
from app.routers.demo import router as demo_router

__all__ = [
    "integrations_router",
    "github_integrations_router",
    "calendar_integrations_router",
    "meetings_router",
    "actions_router",
    "executions_router",
    "audit_router",
    "demo_router",
]
