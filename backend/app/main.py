from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import (
    integrations_router,
    meetings_router,
    actions_router,
    executions_router,
    audit_router,
    demo_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite/Postgres database tables on startup
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Operational Conversational Reasoning Agent: Meeting-to-Jira Engineering Execution Agent",
    lifespan=lifespan
)

# CORS middleware for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev ease
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(integrations_router)
app.include_router(meetings_router)
app.include_router(actions_router)
app.include_router(executions_router)
app.include_router(audit_router)
app.include_router(demo_router)


@app.get("/api/health")
async def healthcheck():
    return {
        "status": "healthy",
        "service": "OCRA Backend",
        "version": settings.APP_VERSION,
        "mock_jira_mode": settings.USE_MOCK_JIRA
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
