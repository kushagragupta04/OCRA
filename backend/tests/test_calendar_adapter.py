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
    GoogleCalendarMockAdapter,
    GoogleCalendarConnector,
)
from app.adapters.connector_base import CalendarConnector
from app.services.execution_service import ExecutionService


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _event(title="Integration Review", key="idem-cal-1"):
    return WorkflowItemPayload(
        title=title,
        description="Review OAuth + frontend integration.",
        idempotency_key=key,
        start_time="2026-09-01T16:00:00",
        end_time="2026-09-01T17:00:00",
        assignee="lead@company.com",
    )


# --------------------------------------------------------------------------- #
# Adapter contract                                                           #
# --------------------------------------------------------------------------- #
def test_calendar_mock_implements_calendar_connector():
    assert isinstance(GoogleCalendarMockAdapter(), CalendarConnector)
    assert isinstance(GoogleCalendarConnector(access_token="x"), CalendarConnector)


def test_registry_returns_calendar_connector():
    conn = get_connector("google_calendar")
    assert isinstance(conn, CalendarConnector)
    assert get_connector("calendar") is conn        # alias


@pytest.mark.asyncio
async def test_calendar_create_success():
    cal = GoogleCalendarMockAdapter()
    result = await cal.create_event(_event())
    assert isinstance(result, ConnectorResult)
    assert result.success is True
    assert result.connector == "google_calendar"
    assert result.external_id == "evt_0001"
    assert result.external_url

    ev = await cal.get_event("evt_0001")
    assert ev is not None
    assert ev.summary == "Integration Review"
    assert ev.start == "2026-09-01T16:00:00"
    assert ev.attendees == ["lead@company.com"]


@pytest.mark.asyncio
async def test_calendar_create_failure_without_token():
    # Real adapter, no OAuth token -> normalized failure (never raises).
    result = await GoogleCalendarConnector(access_token="").create_event(_event())
    assert result.success is False
    assert result.error


@pytest.mark.asyncio
async def test_calendar_update_missing_event_is_failure():
    cal = GoogleCalendarMockAdapter()
    result = await cal.update_event("evt_missing", _event())
    assert result.success is False
    assert "not found" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_calendar_adapter_level_idempotency():
    cal = GoogleCalendarMockAdapter()
    r1 = await cal.create_event(_event(key="dup-cal"))
    r2 = await cal.create_event(_event(key="dup-cal"))
    assert r1.success and r2.success
    assert r1.external_id == r2.external_id
    assert len(await cal.list_events()) == 1


# --------------------------------------------------------------------------- #
# execution_service dispatch + idempotency                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_execution_service_routes_calendar_action_idempotently(test_db: AsyncSession):
    cal = GoogleCalendarMockAdapter()

    test_db.add(Meeting(id="m_cal", title="Auth Roadmap"))
    test_db.add(Action(
        id="a_cal_1",
        meeting_id="m_cal",
        action_type="CREATE",
        item_type="EVENT",
        target_connector="google_calendar",
        summary="Schedule integration review",
        due_at="2026-09-01T16:00:00",
        confidence=0.9,
        risk="LOW",
        reason="Team agreed to review Tuesday 4 PM.",
    ))
    test_db.add(Evidence(
        id="e_cal_1", action_id="a_cal_1", segment_id="s1",
        start_ms=0, end_ms=3000, evidence_text="Let's review Tuesday at 4 PM.",
    ))
    await test_db.commit()

    exec1 = await ExecutionService.execute_action(test_db, "a_cal_1", connector=cal)
    assert exec1.status == "SUCCESS"
    assert exec1.target_connector == "google_calendar"
    assert exec1.operation == "CREATE_EVENT"
    assert exec1.jira_response_id is not None       # reused as generic external id
    assert exec1.external_url

    exec2 = await ExecutionService.execute_action(test_db, "a_cal_1", connector=cal)
    assert exec2.status == "SUCCESS"
    assert exec2.idempotency_key == exec1.idempotency_key
    assert exec2.jira_response_id == exec1.jira_response_id
    assert len(await cal.list_events()) == 1        # no duplicate calendar event on retry
