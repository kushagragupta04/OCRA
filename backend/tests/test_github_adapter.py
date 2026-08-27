import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models.meeting import Meeting
from app.models.action import Action
from app.models.evidence import Evidence
from app.adapters import (
    get_connector,
    ConnectorResult,
    WorkflowItemPayload,
    GithubMockSandboxAdapter,
    GithubConnector,
    GithubMockSandboxAdapter as _GH,
)
from app.adapters.connector_base import TaskConnector
from app.services.execution_service import ExecutionService
from app.config import settings

REPO = "acme/payments-api"


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _item(title="Implement OAuth backend", key="idem-gh-1", repo=REPO):
    return WorkflowItemPayload(
        title=title,
        description="Backend OAuth 2.0 authorization-code flow.",
        assignee="rahul",
        idempotency_key=key,
        extra={"repo": repo},
    )


# --------------------------------------------------------------------------- #
# Adapter contract                                                           #
# --------------------------------------------------------------------------- #
def test_github_mock_implements_task_connector():
    assert isinstance(GithubMockSandboxAdapter(), TaskConnector)
    assert isinstance(GithubConnector(token="x"), TaskConnector)


def test_registry_returns_github_connector():
    conn = get_connector("github")
    assert isinstance(conn, TaskConnector)
    # alias
    assert get_connector("github_issues") is conn


@pytest.mark.asyncio
async def test_github_create_success():
    gh = GithubMockSandboxAdapter()
    repos = await gh.get_repos()
    assert any(r.full_name == REPO for r in repos)

    result = await gh.create_task(_item())
    assert isinstance(result, ConnectorResult)
    assert result.success is True
    assert result.connector == "github"
    assert result.external_key == "42"          # seeded counter starts at 41
    assert result.external_url.endswith(f"/{REPO}/issues/42")

    issue = await gh.get_issue(42)
    assert issue is not None
    assert issue.title == "Implement OAuth backend"
    assert issue.assignees == ["rahul"]
    assert issue.state == "open"


@pytest.mark.asyncio
async def test_github_create_failure_unknown_repo():
    gh = GithubMockSandboxAdapter()
    result = await gh.create_task(_item(repo="acme/nope"))
    assert result.success is False
    assert result.external_id is None
    assert "not found" in (result.error or "").lower()
    assert await gh.list_issues() == []


@pytest.mark.asyncio
async def test_github_real_connector_create_failure_without_token():
    # No GITHUB_TOKEN configured -> normalized ConnectorResult failure (never raises).
    result = await GithubConnector(token="", default_repo=REPO).create_task(_item())
    assert result.success is False
    assert result.error


@pytest.mark.asyncio
async def test_github_adapter_level_idempotency():
    gh = GithubMockSandboxAdapter()
    r1 = await gh.create_task(_item(key="dup-key"))
    r2 = await gh.create_task(_item(key="dup-key"))
    assert r1.success and r2.success
    assert r1.external_key == r2.external_key
    # Retry with the same idempotency key must NOT create a second issue.
    assert len(await gh.list_issues()) == 1


@pytest.mark.asyncio
async def test_github_update_and_close():
    gh = GithubMockSandboxAdapter()
    created = await gh.create_task(_item())
    num = created.external_key

    upd = await gh.update_task(num, _item(title="Implement OAuth backend (v2)"))
    assert upd.success and (await gh.get_issue(int(num))).title.endswith("(v2)")

    closed = await gh.delete_task(num)
    assert closed.success
    assert (await gh.get_issue(int(num))).state == "closed"


# --------------------------------------------------------------------------- #
# execution_service dispatch + idempotency (same key pattern as Jira path)    #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_execution_service_routes_github_action_idempotently(test_db: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_DEFAULT_REPO", REPO)
    gh = GithubMockSandboxAdapter()

    test_db.add(Meeting(id="m_gh", title="Auth Sync"))
    test_db.add(Action(
        id="a_gh_1",
        meeting_id="m_gh",
        action_type="CREATE",
        target_connector="github",
        summary="Create GitHub issue for OAuth backend",
        confidence=0.95,
        risk="LOW",
        reason="Explicit assignment in meeting.",
    ))
    test_db.add(Evidence(
        id="e_gh_1", action_id="a_gh_1", segment_id="s1",
        start_ms=0, end_ms=3000, evidence_text="Rahul will build the OAuth backend.",
    ))
    await test_db.commit()

    exec1 = await ExecutionService.execute_action(test_db, "a_gh_1", connector=gh)
    assert exec1.status == "SUCCESS"
    assert exec1.target_connector == "github"
    assert exec1.jira_issue_key is not None          # reused as generic external key
    assert exec1.external_url

    exec2 = await ExecutionService.execute_action(test_db, "a_gh_1", connector=gh)
    assert exec2.status == "SUCCESS"
    assert exec2.idempotency_key == exec1.idempotency_key
    assert exec2.jira_issue_key == exec1.jira_issue_key
    # Retry created no duplicate GitHub issue.
    assert len(await gh.list_issues()) == 1


@pytest.mark.asyncio
async def test_execution_service_records_github_failure_without_raising(test_db: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_DEFAULT_REPO", "acme/missing-repo")
    gh = GithubMockSandboxAdapter()

    test_db.add(Meeting(id="m_gh2", title="Sync"))
    test_db.add(Action(
        id="a_gh_2", meeting_id="m_gh2", action_type="CREATE", target_connector="github",
        summary="Bad repo issue", confidence=0.9, risk="LOW", reason="x",
    ))
    await test_db.commit()

    exec1 = await ExecutionService.execute_action(test_db, "a_gh_2", connector=gh)
    assert exec1.status == "FAILED"
    assert exec1.error_code == "GITHUB_EXECUTION_ERROR"
    assert exec1.error_message
