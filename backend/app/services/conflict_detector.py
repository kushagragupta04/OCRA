import json
from typing import Optional, Tuple, Dict, Any, List
from app.adapters import JiraAdapter, get_jira_adapter
from app.schemas.action import ConflictDetails
from app.schemas.jira import JiraIssue


class ConflictDetector:
    """
    Detects contradictions and scope conflicts between meeting decisions
    and active work in Jira.
    """

    @staticmethod
    async def evaluate_decision_conflict(
        action_summary: str,
        evidence_text: str,
        target_issue_key: Optional[str] = None,
        project_key: str = "PAY",
        jira: Optional[JiraAdapter] = None
    ) -> Optional[ConflictDetails]:
        adapter = jira or get_jira_adapter()

        # If target issue key is provided or mentioned (e.g. PAY-104)
        if target_issue_key:
            target_issue = await adapter.get_issue(target_issue_key)
            if target_issue:
                return ConflictDetails(
                    affected_issue_key=target_issue.key,
                    affected_issue_summary=target_issue.summary,
                    old_decision=f"Active backlog item {target_issue.key} in status '{target_issue.status}': {target_issue.summary}",
                    new_evidence=evidence_text,
                    recommendation=f"Review whether to cancel, transition, or update scope for {target_issue.key}",
                    risk_level="HIGH"
                )

        # Keyword-based contradiction heuristics across active issues
        evidence_lower = evidence_text.lower()
        if "dropping" in evidence_lower or "deprecate" in evidence_lower or "cancel" in evidence_lower or "no longer doing" in evidence_lower:
            active_issues = await adapter.search_issues(f"project = {project_key}", limit=20)
            for iss in active_issues:
                # E.g. dropping password reset vs PAY-104 Implement Password Reset Flow
                if "password" in evidence_lower and "password" in iss.summary.lower():
                    return ConflictDetails(
                        affected_issue_key=iss.key,
                        affected_issue_summary=iss.summary,
                        old_decision=f"Active backlog item {iss.key} '{iss.summary}' currently in '{iss.status}'.",
                        new_evidence=evidence_text,
                        recommendation=f"Meeting decided to drop/deprecate this flow. Approval required to transition {iss.key} to Closed or remove from sprint.",
                        risk_level="HIGH"
                    )

        return None
