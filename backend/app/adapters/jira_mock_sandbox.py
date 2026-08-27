import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.adapters.jira_base import JiraAdapter
from app.schemas.jira import JiraProject, JiraIssue, JiraUser, JiraTransition, JiraComment


class JiraMockSandboxAdapter(JiraAdapter):
    """
    In-memory, deterministic Jira Cloud v3 Simulator.
    Allows complete, zero-dependency execution and testing of Jira operations,
    transitions, JQL search, duplicate matching, and audit logging.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._projects: Dict[str, JiraProject] = {}
        self._issues: Dict[str, JiraIssue] = {}
        self._users: Dict[str, JiraUser] = {}
        self._issue_counters: Dict[str, int] = {}
        self._seed_default_state()

    def _seed_default_state(self):
        # 1. Seed Projects
        self._projects = {
            "PAY": JiraProject(
                id="proj_1001",
                key="PAY",
                name="Payments & Checkout",
                issue_types=["Task", "Story", "Bug", "Epic"]
            ),
            "AUTH": JiraProject(
                id="proj_1002",
                key="AUTH",
                name="Authentication & IAM",
                issue_types=["Task", "Story", "Bug"]
            ),
            "FRONT": JiraProject(
                id="proj_1003",
                key="FRONT",
                name="Web Frontend",
                issue_types=["Task", "Story", "Bug"]
            ),
        }
        self._issue_counters = {"PAY": 104, "AUTH": 201, "FRONT": 301}

        # 2. Seed Users
        self._users = {
            "acc_rahul_1": JiraUser(account_id="acc_rahul_1", display_name="Rahul Sharma", email="rahul@company.com"),
            "acc_priya_2": JiraUser(account_id="acc_priya_2", display_name="Priya Patel", email="priya@company.com"),
            "acc_alex_3": JiraUser(account_id="acc_alex_3", display_name="Alex Rivera", email="alex@company.com"),
            "acc_sarah_4": JiraUser(account_id="acc_sarah_4", display_name="Sarah Chen", email="sarah@company.com"),
        }

        # 3. Seed Realistic Backlog Issues (including PAY-104 for password-reset conflict test)
        self._issues = {
            "PAY-101": JiraIssue(
                id="iss_101",
                key="PAY-101",
                summary="Set up Stripe Webhooks",
                description="Configure webhook signatures and handle invoice.payment_succeeded events.",
                status="In Progress",
                issue_type="Task",
                assignee=self._users["acc_rahul_1"],
                priority="High",
                due_date="2026-08-30",
                comments=[
                    JiraComment(
                        id="comm_1",
                        author="Rahul Sharma",
                        body="Stripe webhook endpoint scaffolding completed. Working on signature verification.",
                        created=datetime.utcnow()
                    )
                ]
            ),
            "PAY-104": JiraIssue(
                id="iss_104",
                key="PAY-104",
                summary="Implement Password Reset Flow",
                description="Build custom token-based password reset endpoint and email templates.",
                status="To Do",
                issue_type="Task",
                assignee=self._users["acc_rahul_1"],
                priority="Medium",
                due_date="2026-09-05",
                comments=[]
            ),
            "AUTH-201": JiraIssue(
                id="iss_201",
                key="AUTH-201",
                summary="Session Token Refresh & Expiry Handling",
                description="Implement sliding session expiry on Redis and refresh token rotation.",
                status="In Progress",
                issue_type="Task",
                assignee=self._users["acc_priya_2"],
                priority="High",
                due_date="2026-09-01",
                comments=[]
            ),
            "FRONT-301": JiraIssue(
                id="iss_301",
                key="FRONT-301",
                summary="Modernize Navigation Sidebar",
                description="Redesign application navigation with collapsible submenus and responsive drawer.",
                status="Done",
                issue_type="Task",
                assignee=self._users["acc_alex_3"],
                priority="Low",
                due_date="2026-08-25",
                comments=[]
            )
        }

    async def get_projects(self) -> List[JiraProject]:
        return list(self._projects.values())

    async def get_project_metadata(self, project_key: str) -> Dict[str, Any]:
        proj = self._projects.get(project_key)
        if not proj:
            return {}
        return {
            "key": proj.key,
            "name": proj.name,
            "issue_types": proj.issue_types,
            "fields": {
                "summary": {"required": True, "type": "string"},
                "description": {"required": False, "type": "adf"},
                "issuetype": {"required": True, "type": "issuetype"},
                "assignee": {"required": False, "type": "user"},
                "duedate": {"required": False, "type": "date"},
                "priority": {"required": False, "type": "priority"}
            }
        }

    async def search_issues(self, jql: str, fields: Optional[List[str]] = None, limit: int = 20) -> List[JiraIssue]:
        async with self._lock:
            # Parse simple project filter from JQL if present
            results = list(self._issues.values())
            
            # Simple keyword matching across summary and description
            jql_lower = jql.lower()
            if "project" in jql_lower:
                for proj_key in self._projects.keys():
                    if f"project = {proj_key.lower()}" in jql_lower or f'project = "{proj_key.lower()}"' in jql_lower or f"project={proj_key.lower()}" in jql_lower:
                        results = [i for i in results if i.key.startswith(proj_key)]
                        break

            # Search text query if JQL contains text ~ "query"
            if "text ~" in jql_lower or "~" in jql_lower:
                query_tokens = [tok.strip(' "()') for tok in jql_lower.split() if len(tok) > 2 and tok not in ["project", "and", "or", "order", "by", "text", "~", "="]]
                if query_tokens:
                    filtered = []
                    for iss in results:
                        text_corpus = f"{iss.summary} {iss.description or ''}".lower()
                        if any(tok in text_corpus for tok in query_tokens):
                            filtered.append(iss)
                    results = filtered

            return results[:limit]

    async def get_issue(self, issue_key: str) -> Optional[JiraIssue]:
        return self._issues.get(issue_key)

    async def get_transitions(self, issue_key: str) -> List[JiraTransition]:
        issue = self._issues.get(issue_key)
        if not issue:
            return []
        
        # Standard workflow transitions
        all_transitions = [
            JiraTransition(id="11", name="To Do", to_status="To Do"),
            JiraTransition(id="21", name="In Progress", to_status="In Progress"),
            JiraTransition(id="31", name="In Review", to_status="In Review"),
            JiraTransition(id="41", name="Done", to_status="Done"),
            JiraTransition(id="51", name="Blocked", to_status="Blocked"),
        ]
        # Return all except current status
        return [t for t in all_transitions if t.to_status != issue.status]

    async def create_issue(self, payload: Dict[str, Any]) -> JiraIssue:
        async with self._lock:
            fields = payload.get("fields", payload)
            project_data = fields.get("project", {})
            project_key = project_data.get("key", "PAY") if isinstance(project_data, dict) else str(project_data)
            
            counter = self._issue_counters.get(project_key, 100) + 1
            self._issue_counters[project_key] = counter
            new_key = f"{project_key}-{counter}"

            summary = fields.get("summary", "New Action Item")
            
            # Handle ADF or string description
            raw_desc = fields.get("description", "")
            desc_text = raw_desc if isinstance(raw_desc, str) else "Created by OCRA Agent with ADF context"

            assignee_data = fields.get("assignee")
            assignee = None
            if assignee_data:
                if isinstance(assignee_data, dict):
                    acc_id = assignee_data.get("accountId") or assignee_data.get("id")
                    assignee = self._users.get(acc_id)
                elif isinstance(assignee_data, str):
                    assignee = self._find_user_by_query(assignee_data)

            issue_type_data = fields.get("issuetype", {})
            issue_type = issue_type_data.get("name", "Task") if isinstance(issue_type_data, dict) else str(issue_type_data)

            due_date = fields.get("duedate")
            priority_data = fields.get("priority", {})
            priority = priority_data.get("name", "Medium") if isinstance(priority_data, dict) else "Medium"

            new_issue = JiraIssue(
                id=f"iss_{counter}",
                key=new_key,
                summary=summary,
                description=desc_text,
                status="To Do",
                issue_type=issue_type,
                assignee=assignee,
                priority=priority,
                due_date=due_date,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
                comments=[]
            )
            self._issues[new_key] = new_issue
            return new_issue

    async def update_issue(self, issue_key: str, payload: Dict[str, Any]) -> JiraIssue:
        async with self._lock:
            issue = self._issues.get(issue_key)
            if not issue:
                raise ValueError(f"Issue {issue_key} not found in Jira Mock Sandbox")

            fields = payload.get("fields", payload)
            if "summary" in fields:
                issue.summary = fields["summary"]
            if "description" in fields:
                desc = fields["description"]
                issue.description = desc if isinstance(desc, str) else str(desc)
            if "duedate" in fields:
                issue.due_date = fields["duedate"]
            if "priority" in fields:
                p = fields["priority"]
                issue.priority = p.get("name", p) if isinstance(p, dict) else str(p)
            if "assignee" in fields:
                a = fields["assignee"]
                if isinstance(a, dict):
                    issue.assignee = self._users.get(a.get("accountId"))
                elif isinstance(a, str):
                    issue.assignee = self._find_user_by_query(a)

            issue.updated = datetime.utcnow()
            return issue

    async def shift_deadline(self, issue_key: str, new_deadline: str, reason_adf: Optional[Dict[str, Any]] = None) -> JiraIssue:
        async with self._lock:
            issue = self._issues.get(issue_key)
            if not issue:
                raise ValueError(f"Issue {issue_key} not found in Jira Mock Sandbox")
            
            issue.due_date = new_deadline
            issue.updated = datetime.utcnow()
            
            comment_body = f"📅 Due date updated to {new_deadline} following engineering meeting discussion."
            issue.comments.append(JiraComment(
                id=f"comm_{len(issue.comments) + 1}",
                author="OCRA Agent",
                body=comment_body,
                created=datetime.utcnow()
            ))
            return issue

    async def add_comment(self, issue_key: str, comment_adf: Dict[str, Any]) -> Dict[str, Any]:
        async with self._lock:
            issue = self._issues.get(issue_key)
            if not issue:
                raise ValueError(f"Issue {issue_key} not found in Jira Mock Sandbox")

            # Extract plain representation for mock
            body_text = "Comment added by OCRA"
            if isinstance(comment_adf, dict) and "body" in comment_adf:
                body_val = comment_adf["body"]
                if isinstance(body_val, str):
                    body_text = body_val
                elif isinstance(body_val, dict) and "content" in body_val:
                    # extract paragraph text
                    paragraphs = []
                    for block in body_val.get("content", []):
                        for item in block.get("content", []):
                            if "text" in item:
                                paragraphs.append(item["text"])
                    body_text = "\n".join(paragraphs) if paragraphs else "Meeting decision noted."

            new_comment = JiraComment(
                id=f"comm_{len(issue.comments) + 1}",
                author="OCRA Engineering Agent",
                body=body_text,
                created=datetime.utcnow()
            )
            issue.comments.append(new_comment)
            issue.updated = datetime.utcnow()
            return {"id": new_comment.id, "created": new_comment.created.isoformat()}

    async def assign_issue(self, issue_key: str, account_id_or_name: str) -> JiraIssue:
        async with self._lock:
            issue = self._issues.get(issue_key)
            if not issue:
                raise ValueError(f"Issue {issue_key} not found")
            
            user = self._users.get(account_id_or_name) or self._find_user_by_query(account_id_or_name)
            issue.assignee = user
            issue.updated = datetime.utcnow()
            return issue

    async def transition_issue(self, issue_key: str, transition_id_or_name: str) -> JiraIssue:
        async with self._lock:
            issue = self._issues.get(issue_key)
            if not issue:
                raise ValueError(f"Issue {issue_key} not found")

            status_map = {
                "11": "To Do",
                "21": "In Progress",
                "31": "In Review",
                "41": "Done",
                "51": "Blocked",
                "to do": "To Do",
                "in progress": "In Progress",
                "in review": "In Review",
                "done": "Done",
                "blocked": "Blocked",
                "drop": "Done",
                "close": "Done"
            }
            target_status = status_map.get(str(transition_id_or_name).lower(), transition_id_or_name)
            issue.status = target_status
            issue.updated = datetime.utcnow()
            return issue

    async def get_users(self, query: Optional[str] = None) -> List[JiraUser]:
        if not query:
            return list(self._users.values())
        q = query.lower()
        return [u for u in self._users.values() if q in u.display_name.lower() or (u.email and q in u.email.lower())]

    def _find_user_by_query(self, query: str) -> Optional[JiraUser]:
        q = query.lower().strip()
        for u in self._users.values():
            if q in u.display_name.lower() or (u.email and q in u.email.lower()) or q in u.account_id:
                return u
        return None

    def reset(self):
        """Reset mock sandbox to pristine initial state."""
        self._seed_default_state()
