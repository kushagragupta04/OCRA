from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.schemas.jira import JiraProject, JiraIssue, JiraUser, JiraTransition


class JiraAdapter(ABC):
    """
    Abstract Base Class for Jira / Work Management Systems.
    Enforces a standard contract so reasoning engines never directly call HTTP endpoints.
    """

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
