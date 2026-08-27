import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base
from app.models.action import Action
from app.models.jira_config import JiraConfig
from app.services.policy_engine import PolicyEngine
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
async def test_policy_high_confidence_auto_execute(test_db: AsyncSession):
    sandbox = JiraMockSandboxAdapter()
    action = Action(
        id="act_1",
        meeting_id="meet_1",
        action_type="CREATE",
        summary="Build Payment Webhook Signature Validator",
        project_key="PAY",
        owner_account_id="acc_rahul_1",
        owner_name="Rahul",
        confidence=0.95,
        risk="LOW",
        reason="Explicitly committed in sync."
    )

    result = await PolicyEngine.evaluate_action_policy(test_db, action, jira=sandbox)
    assert result["status"] == "AUTO_EXECUTABLE"
    assert result["approval_required"] is False


@pytest.mark.asyncio
async def test_policy_kill_switch_blocking(test_db: AsyncSession):
    sandbox = JiraMockSandboxAdapter()
    
    # Enable Kill Switch in DB
    config = JiraConfig(project_key="PAY", kill_switch_active=True)
    test_db.add(config)
    await test_db.commit()

    action = Action(
        id="act_2",
        meeting_id="meet_1",
        action_type="CREATE",
        summary="Build Payment Webhook Signature Validator",
        project_key="PAY",
        owner_account_id="acc_rahul_1",
        owner_name="Rahul",
        confidence=0.95,
        risk="LOW",
        reason="Explicitly committed."
    )

    result = await PolicyEngine.evaluate_action_policy(test_db, action, jira=sandbox)
    assert result["status"] == "REQUIRES_APPROVAL"
    assert result["approval_required"] is True
    assert "Kill-Switch" in result["policy_reason"]
