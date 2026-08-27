import asyncio
import httpx
from typing import List, Optional, Dict, Any
from app.adapters.jira_base import JiraAdapter
from app.schemas.jira import JiraProject, JiraIssue, JiraUser, JiraTransition, JiraComment
from app.config import settings


class JiraCloudAdapter(JiraAdapter):
    """
    Production Jira Cloud REST API v3 Adapter.
    Uses Atlassian OAuth 2.0 (3LO) Bearer tokens and communicates with Atlassian Cloud gateway.
    """

    def __init__(self, cloud_id: Optional[str] = None, access_token: Optional[str] = None):
        self.cloud_id = cloud_id or settings.JIRA_CLOUD_ID or ""
        self.access_token = access_token or ""
        self.base_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}/rest/api/3" if self.cloud_id else ""

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.access_token or not self.cloud_id:
            raise ValueError("Jira Cloud credentials (access token or cloud ID) are not configured.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=json_data,
                    params=params
                )

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    await asyncio.sleep(retry_after)
                    backoff *= 2
                    continue
                elif response.status_code in [401, 403]:
                    raise PermissionError(f"Jira API Authorization failed: {response.status_code} - {response.text}")
                elif response.status_code >= 400:
                    raise RuntimeError(f"Jira API error {response.status_code}: {response.text}")

                if response.status_code == 204:
                    return {}
                return response.json()

        raise RuntimeError("Jira API request exceeded maximum retry attempts.")

    async def get_projects(self) -> List[JiraProject]:
        data = await self._request("GET", "/project")
        projects = []
        for p in data:
            projects.append(JiraProject(
                id=p.get("id", ""),
                key=p.get("key", ""),
                name=p.get("name", ""),
                issue_types=["Task", "Story", "Bug", "Epic"]
            ))
        return projects

    async def get_project_metadata(self, project_key: str) -> Dict[str, Any]:
        data = await self._request("GET", f"/issue/createmeta/{project_key}/issuetypes")
        return data

    async def search_issues(self, jql: str, fields: Optional[List[str]] = None, limit: int = 20) -> List[JiraIssue]:
        payload = {
            "jql": jql,
            "maxResults": limit,
            "fields": fields or ["summary", "description", "status", "issuetype", "assignee", "priority", "duedate", "comment"]
        }
        data = await self._request("POST", "/search", json_data=payload)
        
        issues = []
        for item in data.get("issues", []):
            f = item.get("fields", {})
            assignee = None
            if f.get("assignee"):
                assignee = JiraUser(
                    account_id=f["assignee"].get("accountId", ""),
                    display_name=f["assignee"].get("displayName", "Unknown"),
                    email=f["assignee"].get("emailAddress"),
                    active=f["assignee"].get("active", True)
                )
            
            issues.append(JiraIssue(
                id=item.get("id", ""),
                key=item.get("key", ""),
                summary=f.get("summary", ""),
                description=str(f.get("description", "")) if f.get("description") else None,
                status=f.get("status", {}).get("name", "To Do"),
                issue_type=f.get("issuetype", {}).get("name", "Task"),
                assignee=assignee,
                priority=f.get("priority", {}).get("name", "Medium") if f.get("priority") else "Medium",
                due_date=f.get("duedate")
            ))
        return issues

    async def get_issue(self, issue_key: str) -> Optional[JiraIssue]:
        try:
            item = await self._request("GET", f"/issue/{issue_key}")
            f = item.get("fields", {})
            assignee = None
            if f.get("assignee"):
                assignee = JiraUser(
                    account_id=f["assignee"].get("accountId", ""),
                    display_name=f["assignee"].get("displayName", "Unknown"),
                    email=f["assignee"].get("emailAddress"),
                    active=f["assignee"].get("active", True)
                )
            return JiraIssue(
                id=item.get("id", ""),
                key=item.get("key", ""),
                summary=f.get("summary", ""),
                description=str(f.get("description", "")) if f.get("description") else None,
                status=f.get("status", {}).get("name", "To Do"),
                issue_type=f.get("issuetype", {}).get("name", "Task"),
                assignee=assignee,
                priority=f.get("priority", {}).get("name", "Medium") if f.get("priority") else "Medium",
                due_date=f.get("duedate")
            )
        except Exception:
            return None

    async def get_transitions(self, issue_key: str) -> List[JiraTransition]:
        data = await self._request("GET", f"/issue/{issue_key}/transitions")
        transitions = []
        for t in data.get("transitions", []):
            transitions.append(JiraTransition(
                id=t.get("id", ""),
                name=t.get("name", ""),
                to_status=t.get("to", {}).get("name", "")
            ))
        return transitions

    async def create_issue(self, payload: Dict[str, Any]) -> JiraIssue:
        data = await self._request("POST", "/issue", json_data=payload)
        key = data.get("key")
        created = await self.get_issue(key)
        if not created:
            raise RuntimeError(f"Issue {key} created but failed to fetch state.")
        return created

    async def update_issue(self, issue_key: str, payload: Dict[str, Any]) -> JiraIssue:
        await self._request("PUT", f"/issue/{issue_key}", json_data=payload)
        updated = await self.get_issue(issue_key)
        if not updated:
            raise RuntimeError(f"Failed to fetch updated state for issue {issue_key}")
        return updated

    async def shift_deadline(self, issue_key: str, new_deadline: str, reason_adf: Optional[Dict[str, Any]] = None) -> JiraIssue:
        payload = {"fields": {"duedate": new_deadline}}
        await self.update_issue(issue_key, payload)
        if reason_adf:
            await self.add_comment(issue_key, reason_adf)
        return await self.get_issue(issue_key)

    async def add_comment(self, issue_key: str, comment_adf: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", f"/issue/{issue_key}/comment", json_data=comment_adf)

    async def assign_issue(self, issue_key: str, account_id_or_name: str) -> JiraIssue:
        payload = {"accountId": account_id_or_name}
        await self._request("PUT", f"/issue/{issue_key}/assignee", json_data=payload)
        return await self.get_issue(issue_key)

    async def transition_issue(self, issue_key: str, transition_id_or_name: str) -> JiraIssue:
        payload = {"transition": {"id": str(transition_id_or_name)}}
        await self._request("POST", f"/issue/{issue_key}/transitions", json_data=payload)
        return await self.get_issue(issue_key)

    async def get_users(self, query: Optional[str] = None) -> List[JiraUser]:
        params = {"query": query or ""}
        data = await self._request("GET", "/user/search", params=params)
        users = []
        for u in data:
            users.append(JiraUser(
                account_id=u.get("accountId", ""),
                display_name=u.get("displayName", "User"),
                email=u.get("emailAddress"),
                active=u.get("active", True)
            ))
        return users
