import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base
from app.models.meeting import Meeting
from app.models.action import Action
from app.models.evidence import Evidence
from app.services.execution_service import ExecutionService
from app.adapters.jira_mock_sandbox import JiraMockSandboxAdapter


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_idempotency_prevents_duplicate_jira_tickets(test_db: AsyncSession):
    sandbox = JiraMockSandboxAdapter()

    # Create meeting and action
    meeting = Meeting(id="meet_idem_1", title="Payment Sync")
    test_db.add(meeting)
    
    action = Action(
        id="act_idem_1",
        meeting_id="meet_idem_1",
        action_type="CREATE",
        summary="Implement Apple Pay Gateway Integration",
        project_key="PAY",
        owner_account_id="acc_rahul_1",
        owner_name="Rahul",
        confidence=0.95,
        risk="LOW",
        reason="Explicit agreement."
    )
    test_db.add(action)

    ev = Evidence(
        id="ev_idem_1",
        action_id="act_idem_1",
        segment_id="seg_01",
        start_ms=0,
        end_ms=4000,
        evidence_text="Rahul will add Apple Pay"
    )
    test_db.add(ev)
    await test_db.commit()

    # First Execution
    exec1 = await ExecutionService.execute_action(test_db, "act_idem_1", jira=sandbox)
    assert exec1.status == "SUCCESS"
    first_jira_key = exec1.jira_issue_key
    assert first_jira_key is not None

    # Second Execution (Retry or duplicate request with same idempotency key)
    exec2 = await ExecutionService.execute_action(test_db, "act_idem_1", jira=sandbox)
    assert exec2.status == "SUCCESS"
    assert exec2.jira_issue_key == first_jira_key
    assert exec2.idempotency_key == exec1.idempotency_key
