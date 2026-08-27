from typing import List, Dict, Any, Optional
from app.adapters import get_jira_adapter, JiraAdapter
from app.schemas.jira import JiraProject, JiraIssue, JiraUser


class JiraContextService:
    @staticmethod
    async def get_project_context(project_key: str = "PAY", jira: Optional[JiraAdapter] = None) -> Dict[str, Any]:
        adapter = jira or get_jira_adapter()
        projects = await adapter.get_projects()
        metadata = await adapter.get_project_metadata(project_key)
        users = await adapter.get_users()
        active_issues = await adapter.search_issues(f"project = {project_key} ORDER BY updated DESC", limit=30)

        return {
            "projects": projects,
            "target_project": next((p for p in projects if p.key == project_key), None),
            "metadata": metadata,
            "users": users,
            "active_issues": active_issues
        }
