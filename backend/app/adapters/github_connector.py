"""GitHub Issues connector (blueprint Section 15.1 — "GitHub / Developer issues").

Implements :class:`TaskConnector` against the GitHub REST API
(``POST /repos/{owner}/{repo}/issues``), with a credential-free in-memory mock
that mirrors :mod:`app.adapters.jira_mock_sandbox` for local dev / demo / tests.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.adapters.connector_base import (
    TaskConnector,
    ConnectorResult,
    WorkflowItemPayload,
)


class GithubRepo(BaseModel):
    id: int
    full_name: str          # "owner/repo"
    html_url: str
    private: bool = False
    open_issues_count: int = 0


class GithubIssue(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str = "open"
    html_url: str
    assignees: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    repo: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


def _resolve_repo(item: WorkflowItemPayload) -> Optional[str]:
    return item.extra.get("repo") or settings.GITHUB_DEFAULT_REPO


# --------------------------------------------------------------------------- #
# Mock / sandbox                                                             #
# --------------------------------------------------------------------------- #
class GithubMockSandboxAdapter(TaskConnector):
    """In-memory GitHub Issues simulator. Deterministic, zero-dependency."""

    connector_name = "github"

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._repos: Dict[str, GithubRepo] = {}
        self._issues: Dict[int, GithubIssue] = {}
        self._counter = 0
        # idempotency_key -> issue number, so retries never create duplicates.
        self._idem: Dict[str, int] = {}
        self._seed()

    def _seed(self) -> None:
        self._repos = {
            "acme/payments-api": GithubRepo(
                id=5001, full_name="acme/payments-api",
                html_url="https://github.com/acme/payments-api", open_issues_count=3,
            ),
            "acme/web-frontend": GithubRepo(
                id=5002, full_name="acme/web-frontend",
                html_url="https://github.com/acme/web-frontend", open_issues_count=1,
            ),
            "acme/infra": GithubRepo(
                id=5003, full_name="acme/infra",
                html_url="https://github.com/acme/infra", private=True, open_issues_count=0,
            ),
        }
        self._counter = 41
        self._issues = {}
        self._idem = {}

    async def get_repos(self) -> List[GithubRepo]:
        return list(self._repos.values())

    async def list_issues(self, repo: Optional[str] = None) -> List[GithubIssue]:
        vals = list(self._issues.values())
        return [i for i in vals if repo is None or i.repo == repo]

    async def get_issue(self, number: int) -> Optional[GithubIssue]:
        return self._issues.get(int(number))

    def _result_for(self, issue: GithubIssue) -> ConnectorResult:
        return ConnectorResult.ok(
            connector="github",
            external_id=str(issue.id),
            external_key=str(issue.number),
            external_url=issue.html_url,
            raw=issue.model_dump(mode="json"),
        )

    async def create_task(self, item: WorkflowItemPayload) -> ConnectorResult:
        repo = _resolve_repo(item)
        if not repo:
            return ConnectorResult.fail("No target GitHub repo (item.extra['repo'] / GITHUB_DEFAULT_REPO).", connector="github")
        if repo not in self._repos:
            return ConnectorResult.fail(f"Repository '{repo}' not found.", connector="github")

        async with self._lock:
            key = item.idempotency_key
            if key and key in self._idem:
                return self._result_for(self._issues[self._idem[key]])

            self._counter += 1
            number = self._counter
            issue = GithubIssue(
                id=90000 + number,
                number=number,
                title=item.title,
                body=item.description or item.reason or "",
                state="open",
                html_url=f"https://github.com/{repo}/issues/{number}",
                assignees=[item.assignee] if item.assignee else [],
                labels=list(item.labels),
                repo=repo,
            )
            self._issues[number] = issue
            self._repos[repo].open_issues_count += 1
            if key:
                self._idem[key] = number
            return self._result_for(issue)

    async def update_task(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        async with self._lock:
            issue = self._issues.get(int(external_id)) if str(external_id).isdigit() else None
            if not issue:
                # external_id may be the numeric issue "number"
                issue = self._issues.get(int(external_id)) if str(external_id).lstrip("-").isdigit() else None
            if not issue:
                return ConnectorResult.fail(f"Issue #{external_id} not found.", connector="github")
            issue.title = item.title or issue.title
            if item.description is not None:
                issue.body = item.description
            if item.assignee:
                issue.assignees = [item.assignee]
            if item.labels:
                issue.labels = list(item.labels)
            issue.updated_at = datetime.utcnow()
            return self._result_for(issue)

    async def delete_task(self, external_id: str) -> ConnectorResult:
        # GitHub REST cannot delete issues — close it (same as the real adapter).
        async with self._lock:
            issue = self._issues.get(int(external_id)) if str(external_id).lstrip("-").isdigit() else None
            if not issue:
                return ConnectorResult.fail(f"Issue #{external_id} not found.", connector="github")
            issue.state = "closed"
            issue.updated_at = datetime.utcnow()
            if issue.repo in self._repos:
                self._repos[issue.repo].open_issues_count = max(0, self._repos[issue.repo].open_issues_count - 1)
            return self._result_for(issue)

    def reset(self) -> None:
        self._seed()


# --------------------------------------------------------------------------- #
# Real GitHub REST adapter                                                    #
# --------------------------------------------------------------------------- #
class GithubConnector(TaskConnector):
    """Production GitHub Issues adapter (REST v3, token auth)."""

    connector_name = "github"

    def __init__(self, token: Optional[str] = None, default_repo: Optional[str] = None) -> None:
        self.token = token or settings.GITHUB_TOKEN or ""
        self.default_repo = default_repo or settings.GITHUB_DEFAULT_REPO
        self.base_url = settings.GITHUB_API_BASE.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.token:
            raise ValueError("GITHUB_TOKEN is not configured.")
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        backoff = 1.0
        for _ in range(3):
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(method, url, headers=self._headers(), json=json_data)
            if resp.status_code in (403, 429) and resp.headers.get("Retry-After"):
                await asyncio.sleep(float(resp.headers["Retry-After"]))
                backoff *= 2
                continue
            if resp.status_code in (401, 403):
                raise PermissionError(f"GitHub authorization failed: {resp.status_code} - {resp.text}")
            if resp.status_code >= 400:
                raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")
            return resp.json() if resp.text else {}
        raise RuntimeError("GitHub API request exceeded maximum retry attempts.")

    async def get_repos(self) -> List[GithubRepo]:
        data = await self._request("GET", "/user/repos?per_page=100")
        return [
            GithubRepo(
                id=r["id"], full_name=r["full_name"], html_url=r["html_url"],
                private=r.get("private", False), open_issues_count=r.get("open_issues_count", 0),
            )
            for r in (data if isinstance(data, list) else [])
        ]

    def _to_issue(self, r: Dict[str, Any], repo: str) -> GithubIssue:
        return GithubIssue(
            id=r["id"], number=r["number"], title=r.get("title", ""), body=r.get("body"),
            state=r.get("state", "open"), html_url=r["html_url"],
            assignees=[a["login"] for a in r.get("assignees", [])],
            labels=[l["name"] if isinstance(l, dict) else str(l) for l in r.get("labels", [])],
            repo=repo,
        )

    async def create_task(self, item: WorkflowItemPayload) -> ConnectorResult:
        repo = _resolve_repo(item)
        if not repo:
            return ConnectorResult.fail("No target GitHub repo configured.", connector="github")
        body: Dict[str, Any] = {"title": item.title, "body": item.description or item.reason or ""}
        if item.assignee:
            body["assignees"] = [item.assignee]
        if item.labels:
            body["labels"] = list(item.labels)
        try:
            r = await self._request("POST", f"/repos/{repo}/issues", json_data=body)
            issue = self._to_issue(r, repo)
            return ConnectorResult.ok(
                connector="github", external_id=str(issue.id), external_key=str(issue.number),
                external_url=issue.html_url, raw=r,
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector="github")

    async def update_task(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        repo = _resolve_repo(item)
        if not repo:
            return ConnectorResult.fail("No target GitHub repo configured.", connector="github")
        body: Dict[str, Any] = {"title": item.title}
        if item.description is not None:
            body["body"] = item.description
        try:
            r = await self._request("PATCH", f"/repos/{repo}/issues/{external_id}", json_data=body)
            issue = self._to_issue(r, repo)
            return ConnectorResult.ok(
                connector="github", external_id=str(issue.id), external_key=str(issue.number),
                external_url=issue.html_url, raw=r,
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector="github")

    async def delete_task(self, external_id: str) -> ConnectorResult:
        repo = self.default_repo
        if not repo:
            return ConnectorResult.fail("No target GitHub repo configured.", connector="github")
        try:
            r = await self._request(
                "PATCH", f"/repos/{repo}/issues/{external_id}", json_data={"state": "closed"}
            )
            return ConnectorResult.ok(
                connector="github", external_id=str(r.get("id")), external_key=str(r.get("number")),
                external_url=r.get("html_url"), raw=r,
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector="github")
