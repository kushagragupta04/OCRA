import pytest
from app.services.duplicate_detector import DuplicateDetector
from app.services.conflict_detector import ConflictDetector
from app.adapters.jira_mock_sandbox import JiraMockSandboxAdapter


@pytest.mark.asyncio
async def test_duplicate_detector_scoring():
    sandbox = JiraMockSandboxAdapter()

    # Exact / Strong Duplicate
    status, match, score = await DuplicateDetector.evaluate_proposed_create(
        summary="Set up Stripe Webhooks integration",
        description="Configure webhook signatures",
        project_key="PAY",
        jira=sandbox
    )
    assert status in ["STRONG_DUPLICATE", "POSSIBLE_DUPLICATE"]
    assert match is not None
    assert match.key == "PAY-101"
    assert score >= 0.50

    # No Match
    status_no, match_no, score_no = await DuplicateDetector.evaluate_proposed_create(
        summary="Completely unique AI recommendation engine",
        description="Machine learning model deployment",
        project_key="PAY",
        jira=sandbox
    )
    assert status_no == "NO_MATCH"
    assert match_no is None


@pytest.mark.asyncio
async def test_conflict_detector_with_password_reset():
    sandbox = JiraMockSandboxAdapter()

    # Scenario: Decision drops password reset approach
    conflict = await ConflictDetector.evaluate_decision_conflict(
        action_summary="Deprecate password reset flow",
        evidence_text="We are dropping the old password-reset approach in favor of OAuth.",
        target_issue_key="PAY-104",
        project_key="PAY",
        jira=sandbox
    )
    assert conflict is not None
    assert conflict.affected_issue_key == "PAY-104"
    assert "PAY-104" in conflict.old_decision
    assert conflict.risk_level == "HIGH"
