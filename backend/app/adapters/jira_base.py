from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.schemas.jira import JiraProject, JiraIssue, JiraUser, JiraTransition
from app.adapters.connector_base import (
    TaskConnector,
    ConnectorResult,
    WorkflowItemPayload,
)
from app.config import settings


class JiraAdapter(TaskConnector, ABC):
    """
    Abstract Base Class for Jira / Work Management Systems.
    Enforces a standard contract so reasoning engines never directly call HTTP endpoints.

    Implements the blueprint's :class:`TaskConnector` contract (Section 15) on top of
    the Jira-native operations below, so Jira is just one ``TaskConnector`` among many.
    """

    connector_name = "jira"

    @abstractmethod
    async def get_projects(self) -> List[JiraProject]:
        """Fetch accessible Jira projects."""
        pass

    @abstractmethod
    async def get_project_metadata(self, project_key: str) -> Dict[str, Any]:
        """Fetch project metadata, issue types, and create screen fields."""
        pass

    @abstractmethod
    async def search_issues(self, jql: str, fields: Optional[List[str]] = None, limit: int = 20) -> List[JiraIssue]:
        """Search issues using JQL with candidate filtering."""
        pass

    @abstractmethod
    async def get_issue(self, issue_key: str) -> Optional[JiraIssue]:
        """Fetch a single Jira issue by key or ID."""
        pass

    @abstractmethod
    async def get_transitions(self, issue_key: str) -> List[JiraTransition]:
        """Fetch available workflow transitions for an issue."""
        pass

    @abstractmethod
    async def create_issue(self, payload: Dict[str, Any]) -> JiraIssue:
        """Create a new Jira issue."""
        pass

    @abstractmethod
    async def update_issue(self, issue_key: str, payload: Dict[str, Any]) -> JiraIssue:
        """Update fields of an existing Jira issue."""
        pass

    @abstractmethod
    async def shift_deadline(self, issue_key: str, new_deadline: str, reason_adf: Optional[Dict[str, Any]] = None) -> JiraIssue:
        """Update due date of an existing Jira issue and log evidence comment."""
        pass

    @abstractmethod
    async def add_comment(self, issue_key: str, comment_adf: Dict[str, Any]) -> Dict[str, Any]:
        """Add an ADF-formatted comment to an issue."""
        pass

    @abstractmethod
    async def assign_issue(self, issue_key: str, account_id_or_name: str) -> JiraIssue:
        """Assign an issue to a Jira user."""
        pass

    @abstractmethod
    async def transition_issue(self, issue_key: str, transition_id_or_name: str) -> JiraIssue:
        """Execute a workflow transition on an issue."""
        pass

    @abstractmethod
    async def get_users(self, query: Optional[str] = None) -> List[JiraUser]:
        """Search Jira users accessible to the project."""
        pass

    # ------------------------------------------------------------------ #
    # TaskConnector contract (blueprint Section 15) — concrete, shared    #
    # by every Jira adapter (cloud + mock). Translates the normalized     #
    # WorkflowItemPayload into Jira's field schema.                       #
    # ------------------------------------------------------------------ #
    def _issue_url(self, issue_key: str) -> Optional[str]:
        site = (settings.JIRA_SITE_URL or "").rstrip("/")
        return f"{site}/browse/{issue_key}" if site else None

    def _payload_to_fields(self, item: WorkflowItemPayload) -> Dict[str, Any]:
        fields: Dict[str, Any] = {
            "project": {"key": item.extra.get("project_key") or "PAY"},
            "summary": item.title,
            "issuetype": {"name": item.extra.get("issue_type") or "Task"},
            "priority": {"name": item.priority or "Medium"},
        }
        if item.description:
            fields["description"] = item.description
        if item.due_at:
            fields["duedate"] = item.due_at
        if item.assignee:
            fields["assignee"] = {"accountId": item.assignee}
        return fields

    async def create_task(self, item: WorkflowItemPayload) -> ConnectorResult:
        try:
            issue = await self.create_issue({"fields": self._payload_to_fields(item)})
            return ConnectorResult.ok(
                connector=self.connector_name,
                external_id=issue.id,
                external_key=issue.key,
                external_url=self._issue_url(issue.key),
                raw=issue.model_dump(mode="json"),
            )
        except Exception as e:  # noqa: BLE001 - surfaced as a ConnectorResult
            return ConnectorResult.fail(str(e), connector=self.connector_name)

    async def update_task(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        try:
            issue = await self.update_issue(external_id, {"fields": self._payload_to_fields(item)})
            return ConnectorResult.ok(
                connector=self.connector_name,
                external_id=issue.id,
                external_key=issue.key,
                external_url=self._issue_url(issue.key),
                raw=issue.model_dump(mode="json"),
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector=self.connector_name)

    async def delete_task(self, external_id: str) -> ConnectorResult:
        # Jira issues are not hard-deleted from the execution path; soft-close instead.
        try:
            issue = await self.transition_issue(external_id, "Done")
            return ConnectorResult.ok(
                connector=self.connector_name,
                external_id=getattr(issue, "id", None),
                external_key=getattr(issue, "key", external_id),
                external_url=self._issue_url(getattr(issue, "key", external_id)),
                raw={"soft_deleted": True},
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector=self.connector_name)
