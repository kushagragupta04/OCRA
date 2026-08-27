from typing import Optional, Union

from app.adapters.jira_base import JiraAdapter
from app.adapters.jira_mock_sandbox import JiraMockSandboxAdapter
from app.adapters.jira_cloud import JiraCloudAdapter
from app.adapters.jira_adf import JiraADFBuilder
from app.adapters.connector_base import (
    TaskConnector,
    CalendarConnector,
    ConnectorResult,
    WorkflowItemPayload,
)
from app.adapters.github_connector import GithubConnector, GithubMockSandboxAdapter
from app.adapters.google_calendar_connector import (
    GoogleCalendarConnector,
    GoogleCalendarMockAdapter,
)
from app.config import settings

# Global singleton instances for the mocks so state is preserved across endpoints
# in demo / dev mode (mirrors the original Jira sandbox singleton).
_sandbox_instance = JiraMockSandboxAdapter()
_github_sandbox_instance = GithubMockSandboxAdapter()
_calendar_sandbox_instance = GoogleCalendarMockAdapter()


def get_jira_adapter(force_mock: Optional[bool] = None) -> JiraAdapter:
    use_mock = settings.USE_MOCK_JIRA if force_mock is None else force_mock
    if use_mock:
        return _sandbox_instance
    return JiraCloudAdapter()


def get_sandbox_adapter() -> JiraMockSandboxAdapter:
    return _sandbox_instance


def get_github_adapter(force_mock: Optional[bool] = None) -> TaskConnector:
    use_mock = settings.USE_MOCK_GITHUB if force_mock is None else force_mock
    # Fall back to mock when no credentials are configured (same rule as Jira).
    if use_mock or not settings.GITHUB_TOKEN:
        return _github_sandbox_instance
    return GithubConnector()


def get_calendar_adapter(force_mock: Optional[bool] = None) -> CalendarConnector:
    use_mock = settings.USE_MOCK_CALENDAR if force_mock is None else force_mock
    if use_mock or not settings.GOOGLE_OAUTH_ACCESS_TOKEN:
        return _calendar_sandbox_instance
    return GoogleCalendarConnector()


def get_github_sandbox_adapter() -> GithubMockSandboxAdapter:
    return _github_sandbox_instance


def get_calendar_sandbox_adapter() -> GoogleCalendarMockAdapter:
    return _calendar_sandbox_instance


# Canonical connector names + aliases used on WorkflowItem.target_connector.
_CONNECTOR_ALIASES = {
    "jira": "jira",
    "github": "github",
    "github_issues": "github",
    "google_calendar": "google_calendar",
    "googlecalendar": "google_calendar",
    "calendar": "google_calendar",
    "gcal": "google_calendar",
}


def get_connector(
    name: Optional[str], force_mock: Optional[bool] = None
) -> Union[TaskConnector, CalendarConnector]:
    """Return the adapter for a ``WorkflowItem.target_connector`` value.

    Defaults to Jira when unset. Each connector self-selects mock vs real based on
    its ``USE_MOCK_*`` flag and whether credentials are configured.
    """
    canonical = _CONNECTOR_ALIASES.get((name or "jira").strip().lower())
    if canonical is None:
        raise ValueError(f"Unknown connector '{name}'. Known: {sorted(set(_CONNECTOR_ALIASES.values()))}")
    if canonical == "jira":
        return get_jira_adapter(force_mock)
    if canonical == "github":
        return get_github_adapter(force_mock)
    return get_calendar_adapter(force_mock)


__all__ = [
    "JiraAdapter",
    "JiraMockSandboxAdapter",
    "JiraCloudAdapter",
    "JiraADFBuilder",
    "TaskConnector",
    "CalendarConnector",
    "ConnectorResult",
    "WorkflowItemPayload",
    "GithubConnector",
    "GithubMockSandboxAdapter",
    "GoogleCalendarConnector",
    "GoogleCalendarMockAdapter",
    "get_jira_adapter",
    "get_sandbox_adapter",
    "get_github_adapter",
    "get_calendar_adapter",
    "get_github_sandbox_adapter",
    "get_calendar_sandbox_adapter",
    "get_connector",
]
