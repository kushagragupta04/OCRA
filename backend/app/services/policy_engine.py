from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.action import Action
from app.models.approval import Approval
from app.models.jira_config import JiraConfig
from app.services.duplicate_detector import DuplicateDetector
from app.services.conflict_detector import ConflictDetector
from app.adapters import JiraAdapter, get_jira_adapter
from app.config import settings
import uuid
import json


class PolicyEngine:
    @classmethod
    async def evaluate_action_policy(
        cls,
        db: AsyncSession,
        action: Action,
        evidence_text: str = "",
        jira: Optional[JiraAdapter] = None
    ) -> Dict[str, Any]:
        """
        Evaluates risk, confidence, duplicate match, conflict state, and policy config.
        Returns: {
            "status": "AUTO_EXECUTED" | "REQUIRES_APPROVAL" | "BLOCKED",
            "approval_required": bool,
            "policy_reason": str,
            "risk": "LOW" | "MEDIUM" | "HIGH"
        }
        """
        adapter = jira or get_jira_adapter()

        # 1. Fetch project policy configuration
        stmt = select(JiraConfig).where(JiraConfig.project_key == action.project_key)
        config = (await db.execute(stmt)).scalars().first()

        auto_execute_enabled = config.auto_execute_enabled if config else settings.AUTO_EXECUTE_ENABLED
        min_confidence = config.min_confidence_threshold if config else settings.MIN_CONFIDENCE_THRESHOLD
        kill_switch = config.kill_switch_active if config else settings.KILL_SWITCH_ACTIVE

        # 2. Check Master Kill Switch
        if kill_switch:
            return {
                "status": "REQUIRES_APPROVAL",
                "approval_required": True,
                "policy_reason": "Workspace Kill-Switch is active. All Jira mutations require human sign-off.",
                "risk": "HIGH"
            }

        # 3. Check Conflict / Contradiction
        if action.action_type == "CONFLICT" or action.conflict_payload:
            return {
                "status": "REQUIRES_APPROVAL",
                "approval_required": True,
                "policy_reason": "Decision contradicts existing Jira issue or active backlog scope. Manual review required.",
                "risk": "HIGH"
            }

        # 4. Check Duplicate Detection on CREATE
        if action.action_type == "CREATE":
            dup_status, match_issue, dup_score = await DuplicateDetector.evaluate_proposed_create(
                summary=action.summary,
                description=action.description,
                project_key=action.project_key,
                jira=adapter
            )
            if dup_status == "STRONG_DUPLICATE" and match_issue:
                action.target_issue_key = match_issue.key
                return {
                    "status": "REQUIRES_APPROVAL",
                    "approval_required": True,
                    "policy_reason": f"Strong duplicate detected against existing issue {match_issue.key} ('{match_issue.summary}'). Similarity: {int(dup_score * 100)}%.",
                    "risk": "MEDIUM"
                }
            elif dup_status == "POSSIBLE_DUPLICATE" and match_issue:
                return {
                    "status": "REQUIRES_APPROVAL",
                    "approval_required": True,
                    "policy_reason": f"Possible duplicate of issue {match_issue.key} ('{match_issue.summary}'). Similarity: {int(dup_score * 100)}%.",
                    "risk": "MEDIUM"
                }

        # 5. Check Confidence Threshold
        if action.confidence < min_confidence:
            return {
                "status": "REQUIRES_APPROVAL",
                "approval_required": True,
                "policy_reason": f"Extraction confidence ({int(action.confidence * 100)}%) is below project threshold ({int(min_confidence * 100)}%).",
                "risk": "MEDIUM"
            }

        # 6. Check Owner Ambiguity for Assignment / Task Creation
        if not action.owner_account_id and not action.owner_name and action.action_type in ["ASSIGN", "CREATE"]:
            return {
                "status": "REQUIRES_APPROVAL",
                "approval_required": True,
                "policy_reason": "Owner was not explicitly identified in the meeting.",
                "risk": "MEDIUM"
            }

        # 7. Check High Risk Actions
        if action.risk == "HIGH" or action.action_type in ["TRANSITION", "DELETE", "CLOSE"]:
            return {
                "status": "REQUIRES_APPROVAL",
                "approval_required": True,
                "policy_reason": f"Action type '{action.action_type}' carries high impact.",
                "risk": "HIGH"
            }

        # 8. If Project Auto-Execute Policy is disabled
        if not auto_execute_enabled:
            return {
                "status": "REQUIRES_APPROVAL",
                "approval_required": True,
                "policy_reason": "Project policy has auto-execution disabled. Manual approval needed.",
                "risk": action.risk
            }

        # 9. Otherwise, Safe High-Confidence Auto-Execution
        return {
            "status": "AUTO_EXECUTABLE",
            "approval_required": False,
            "policy_reason": "Action is high-confidence, explicit, and verified against duplicates.",
            "risk": "LOW"
        }
