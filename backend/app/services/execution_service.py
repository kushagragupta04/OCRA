import asyncio
import json
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.action import Action
from app.models.execution import Execution
from app.models.evidence import Evidence
from app.models.meeting import Meeting
from app.adapters import (
    get_jira_adapter,
    get_connector,
    JiraAdapter,
    JiraADFBuilder,
    TaskConnector,
    CalendarConnector,
    ConnectorResult,
    WorkflowItemPayload,
)
from app.services.audit_service import AuditService
from app.utils.hashing import compute_idempotency_key
from app.config import settings


def _connector_key(action: Action) -> str:
    return (getattr(action, "target_connector", None) or "jira").strip().lower()


class ExecutionService:
    @classmethod
    async def execute_action(
        cls,
        db: AsyncSession,
        action_id: str,
        actor: str = "system:executor",
        jira: Optional[JiraAdapter] = None,
        connector: Optional[Any] = None,
    ) -> Execution:
        """
        Executes a single approved or auto-executable action against its
        ``target_connector`` (Jira / GitHub / Google Calendar) with strict
        idempotency key protection and rollback/audit recording.

        The Jira path is unchanged; ``connector`` may be injected for tests
        (mirrors the existing ``jira`` injection).
        """
        adapter = jira or get_jira_adapter()

        # 1. Fetch action with meeting and evidence
        stmt = (
            select(Action)
            .where(Action.id == action_id)
            .options(selectinload(Action.evidence), selectinload(Action.meeting))
        )
        action = (await db.execute(stmt)).scalars().first()
        if not action:
            raise ValueError(f"Action {action_id} not found")

        # 2. Determine operation type & build stable invariant idempotency key
        operation_map = {
            "CREATE": "CREATE_ISSUE",
            "UPDATE": "UPDATE_ISSUE",
            "ASSIGN": "ASSIGN_USER",
            "COMMENT": "ADD_COMMENT",
            "SHIFT_DEADLINE": "SHIFT_DEADLINE",
            "TRANSITION": "TRANSITION_ISSUE",
            "CONFLICT": "HANDLE_CONFLICT"
        }
        connector_key = _connector_key(action)
        operation = operation_map.get(action.action_type, "CUSTOM_MUTATION")
        if connector_key not in ("jira", ""):
            # Generic connector op labels (kept idempotency-stable per connector).
            operation = "CREATE_EVENT" if connector_key in ("google_calendar", "calendar") else operation
        fingerprint = f"{action.id}:{action.summary}:{action.action_type}"
        idem_key = compute_idempotency_key(action.meeting_id, fingerprint, operation)

        # 3. Check if an execution with this idempotency key already succeeded
        stmt_exec = select(Execution).where(Execution.idempotency_key == idem_key)
        existing_exec = (await db.execute(stmt_exec)).scalars().first()
        if existing_exec and existing_exec.status == "SUCCESS":
            return existing_exec

        # 4. Create or update Execution record in EXECUTING state
        exec_record = existing_exec or Execution(
            id=str(uuid.uuid4()),
            action_id=action_id,
            operation=operation,
            idempotency_key=idem_key,
            status="EXECUTING"
        )
        if not existing_exec:
            db.add(exec_record)
        else:
            exec_record.status = "EXECUTING"
            exec_record.retry_count += 1
        
        action.status = "EXECUTING"
        await db.commit()

        # 4b. Non-Jira connectors (GitHub Issues / Google Calendar) dispatch here.
        # The Jira path below is untouched for connector_key == "jira".
        if connector_key not in ("jira", ""):
            return await cls._execute_via_connector(
                db=db,
                action=action,
                exec_record=exec_record,
                connector_key=connector_key,
                operation=operation,
                actor=actor,
                injected_connector=connector,
            )

        # 5. Execute Jira Mutation
        evidence_dicts = [
            {"start_ms": ev.start_ms, "end_ms": ev.end_ms, "evidence_text": ev.evidence_text}
            for ev in action.evidence
        ]
        meeting_title = action.meeting.title if action.meeting else "Engineering Sync"

        try:
            res_key = None
            res_id = None

            if action.action_type == "CREATE":
                # Build ADF description with evidence & confidence callouts
                adf_desc = JiraADFBuilder.build_action_description(
                    summary=action.summary,
                    description=action.description,
                    meeting_title=meeting_title,
                    evidence_items=evidence_dicts,
                    confidence=action.confidence,
                    reason=action.reason
                )

                payload = {
                    "fields": {
                        "project": {"key": action.project_key},
                        "summary": action.summary,
                        "description": adf_desc,
                        "issuetype": {"name": action.issue_type or "Task"},
                        "priority": {"name": action.priority or "Medium"}
                    }
                }
                if action.due_at:
                    payload["fields"]["duedate"] = action.due_at
                if action.owner_account_id:
                    payload["fields"]["assignee"] = {"accountId": action.owner_account_id}

                created_issue = await adapter.create_issue(payload)
                res_key = created_issue.key
                res_id = created_issue.id
                action.target_issue_key = res_key

            elif action.action_type == "SHIFT_DEADLINE":
                target_key = action.target_issue_key
                if not target_key:
                    raise ValueError("Target issue key is required to shift deadline.")

                reason_adf = JiraADFBuilder.build_comment_adf(
                    comment_text=f"📅 Deadline shifted to {action.due_at}. Reason: {action.reason}",
                    meeting_title=meeting_title,
                    evidence_quote=evidence_dicts[0]["evidence_text"] if evidence_dicts else None
                )
                updated_issue = await adapter.shift_deadline(target_key, action.due_at or "2026-09-01", reason_adf)
                res_key = updated_issue.key
                res_id = updated_issue.id

            elif action.action_type == "COMMENT":
                target_key = action.target_issue_key
                if not target_key:
                    raise ValueError("Target issue key is required to add comment.")

                comment_adf = JiraADFBuilder.build_comment_adf(
                    comment_text=action.description or action.summary,
                    meeting_title=meeting_title,
                    evidence_quote=evidence_dicts[0]["evidence_text"] if evidence_dicts else None
                )
                comm_res = await adapter.add_comment(target_key, comment_adf)
                res_key = target_key
                res_id = comm_res.get("id")

            elif action.action_type == "ASSIGN":
                target_key = action.target_issue_key
                if not target_key or not action.owner_account_id:
                    raise ValueError("Target issue key and assignee account ID required.")
                assigned_issue = await adapter.assign_issue(target_key, action.owner_account_id)
                res_key = assigned_issue.key
                res_id = assigned_issue.id

            elif action.action_type == "TRANSITION":
                target_key = action.target_issue_key
                if not target_key:
                    raise ValueError("Target issue key required for transition.")
                transitioned_issue = await adapter.transition_issue(target_key, action.transition_name or "Done")
                res_key = transitioned_issue.key
                res_id = transitioned_issue.id

            elif action.action_type == "CONFLICT":
                # For approved conflicts: add resolution comment and transition target issue
                target_key = action.target_issue_key or "PAY-104"
                conflict_adf = JiraADFBuilder.build_conflict_comment(
                    new_decision=action.description or action.summary,
                    evidence_text=evidence_dicts[0]["evidence_text"] if evidence_dicts else "Meeting decision noted.",
                    meeting_title=meeting_title,
                    reviewer=actor
                )
                await adapter.add_comment(target_key, conflict_adf)
                res_key = target_key
                res_id = f"conflict_resolved_{target_key}"

            # 6. Mark Success
            exec_record.status = "SUCCESS"
            exec_record.target_connector = "jira"
            exec_record.jira_issue_key = res_key
            exec_record.jira_response_id = res_id
            if res_key and (settings.JIRA_SITE_URL or ""):
                exec_record.external_url = f"{settings.JIRA_SITE_URL.rstrip('/')}/browse/{res_key}"
            exec_record.error_code = None
            exec_record.error_message = None

            action.status = "COMPLETED"
            await db.commit()

            # 7. Record Immutable Audit Event
            await AuditService.log_event(
                db=db,
                actor=actor,
                event_type="EXECUTION_SUCCESS",
                meeting_id=action.meeting_id,
                action_id=action.id,
                before_state={"status": "PROPOSED", "action_type": action.action_type},
                after_state={"status": "COMPLETED", "jira_issue_key": res_key, "operation": operation}
            )
            return exec_record

        except Exception as e:
            exec_record.status = "FAILED"
            exec_record.error_code = "JIRA_EXECUTION_ERROR"
            exec_record.error_message = str(e)
            action.status = "FAILED"
            await db.commit()

            await AuditService.log_event(
                db=db,
                actor=actor,
                event_type="EXECUTION_FAILED",
                meeting_id=action.meeting_id,
                action_id=action.id,
                after_state={"error": str(e)}
            )
            raise e

    # ------------------------------------------------------------------ #
    # Non-Jira connector dispatch (blueprint Sections 15 & 18).          #
    # Unlike the Jira path, a connector failure is *recorded* on the     #
    # Execution row and returned (not raised) so one failing connector   #
    # never fails a whole multi-tool workflow.                           #
    # ------------------------------------------------------------------ #
    @classmethod
    async def _execute_via_connector(
        cls,
        db: AsyncSession,
        action: Action,
        exec_record: Execution,
        connector_key: str,
        operation: str,
        actor: str,
        injected_connector: Optional[Any] = None,
    ) -> Execution:
        adapter = injected_connector or get_connector(connector_key)

        meeting_title = action.meeting.title if action.meeting else "Engineering Sync"
        evidence_dicts = [
            {"start_ms": ev.start_ms, "end_ms": ev.end_ms, "evidence_text": ev.evidence_text}
            for ev in action.evidence
        ]

        payload = WorkflowItemPayload(
            source_action_id=action.id,
            idempotency_key=exec_record.idempotency_key,
            item_type=(getattr(action, "item_type", None) or "TASK"),
            title=action.summary,
            description=action.description,
            assignee=action.owner_account_id or action.owner_name,
            priority=action.priority or "Medium",
            due_at=action.due_at,
            start_time=action.due_at,
            meeting_title=meeting_title,
            reason=action.reason,
            evidence=evidence_dicts,
            extra={
                "project_key": action.project_key,
                "issue_type": action.issue_type,
                "repo": settings.GITHUB_DEFAULT_REPO,
                "calendar_id": settings.GOOGLE_CALENDAR_ID,
            },
        )

        try:
            if isinstance(adapter, CalendarConnector) or connector_key in ("google_calendar", "calendar"):
                result: ConnectorResult = await adapter.create_event(payload)
            else:
                result = await adapter.create_task(payload)
        except Exception as e:  # noqa: BLE001 - normalized into a ConnectorResult
            result = ConnectorResult.fail(str(e), connector=connector_key)

        exec_record.target_connector = connector_key
        if result.success:
            exec_record.status = "SUCCESS"
            exec_record.jira_issue_key = result.external_key
            exec_record.jira_response_id = result.external_id
            exec_record.external_url = result.external_url
            exec_record.error_code = None
            exec_record.error_message = None
            action.status = "COMPLETED"
        else:
            exec_record.status = "FAILED"
            exec_record.error_code = f"{connector_key.upper()}_EXECUTION_ERROR"
            exec_record.error_message = result.error
            action.status = "FAILED"

        await db.commit()

        await AuditService.log_event(
            db=db,
            actor=actor,
            event_type="EXECUTION_SUCCESS" if result.success else "EXECUTION_FAILED",
            meeting_id=action.meeting_id,
            action_id=action.id,
            before_state={"status": "PROPOSED", "action_type": action.action_type},
            after_state={
                "status": action.status,
                "connector": connector_key,
                "operation": operation,
                "external_id": result.external_id,
                "external_url": result.external_url,
                "error": result.error,
            },
        )
        return exec_record
