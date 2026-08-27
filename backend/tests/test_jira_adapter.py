import pytest
from app.adapters.jira_mock_sandbox import JiraMockSandboxAdapter
from app.adapters.jira_adf import JiraADFBuilder


@pytest.mark.asyncio
async def test_mock_sandbox_crud_and_transitions():
    sandbox = JiraMockSandboxAdapter()
    
    # 1. Projects
    projects = await sandbox.get_projects()
    assert len(projects) >= 3
    assert any(p.key == "PAY" for p in projects)

    # 2. Search initial issues
    issues = await sandbox.search_issues("project = PAY")
    assert any(i.key == "PAY-104" for i in issues)

    # 3. Create Issue
    new_issue = await sandbox.create_issue({
        "fields": {
            "project": {"key": "PAY"},
            "summary": "Setup OAuth 2.0 Provider",
            "description": "Backend implementation",
            "priority": {"name": "High"},
            "duedate": "2026-08-28"
        }
    })
    assert new_issue.key == "PAY-105"
    assert new_issue.summary == "Setup OAuth 2.0 Provider"
    assert new_issue.due_date == "2026-08-28"

    # 4. Shift Deadline
    shifted = await sandbox.shift_deadline("PAY-105", "2026-09-02")
    assert shifted.due_date == "2026-09-02"
    assert len(shifted.comments) == 1

    # 5. Transitions
    transitions = await sandbox.get_transitions("PAY-105")
    assert len(transitions) > 0
    await sandbox.transition_issue("PAY-105", "In Progress")
    updated = await sandbox.get_issue("PAY-105")
    assert updated.status == "In Progress"


def test_adf_builder():
    adf = JiraADFBuilder.build_action_description(
        summary="Test Action",
        description="Detailed notes",
        meeting_title="Architecture Sync",
        evidence_items=[{"start_ms": 0, "end_ms": 4000, "evidence_text": "We will build this"}],
        confidence=0.95,
        reason="Assigned in meeting"
    )
    assert adf["version"] == 1
    assert adf["type"] == "doc"
    assert len(adf["content"]) >= 3
