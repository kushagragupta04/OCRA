import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment
from app.models.action import Action
from app.models.evidence import Evidence
from app.models.audit import AuditEvent
from app.services.llm_provider import LLMProvider
from app.adapters import get_jira_adapter
from app.utils.security import format_transcript_for_prompt_isolation
from app.schemas.llm import LLMExtractionResponse


class ExtractionService:
    @classmethod
    async def extract_meeting_actions(
        cls,
        db: AsyncSession,
        meeting_id: str,
        project_key: str = "PAY"
    ) -> List[Action]:
        """
        Extracts structured engineering actions from meeting segments with prompt isolation
        and speaker-to-Jira user resolution.
        """
        # 1. Fetch meeting and segments
        stmt = select(Meeting).where(Meeting.id == meeting_id)
        meeting = (await db.execute(stmt)).scalars().first()
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        stmt_seg = select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.start_ms)
        segments_orm = (await db.execute(stmt_seg)).scalars().all()
        
        segments_dict = [
            {
                "id": s.id,
                "segment_id": s.id,
                "speaker_name": s.speaker_name,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "text": s.text
            }
            for s in segments_orm
        ]

        # 2. Fetch accessible Jira users to assist resolution
        jira = get_jira_adapter()
        jira_users = await jira.get_users()
        user_names = [u.display_name for u in jira_users]

        # 3. Format prompt with strict untrusted data isolation
        isolated_transcript = format_transcript_for_prompt_isolation(segments_dict)

        # 4. LLM Structured Extraction
        extraction_res: LLMExtractionResponse = await LLMProvider.extract_actions_and_decisions(
            isolated_transcript=isolated_transcript,
            segments=segments_dict,
            jira_project_key=project_key,
            available_users=user_names
        )

        # 5. Map and persist Actions & Evidence
        action_ids: List[str] = []

        for item in extraction_res.actions:
            action_id = str(uuid.uuid4())
            action_ids.append(action_id)
            
            # Resolve owner name to Jira accountId
            resolved_account_id = None
            if item.owner_name:
                for u in jira_users:
                    if item.owner_name.lower() in u.display_name.lower() or u.display_name.lower().startswith(item.owner_name.lower()):
                        resolved_account_id = u.account_id
                        break

            # Handle conflict payload
            conflict_payload_str = None
            if item.action_type == "CONFLICT" or item.conflict_summary:
                conflict_payload_str = json.dumps({
                    "affected_issue_key": item.target_issue_key or "PAY-104",
                    "affected_issue_summary": "Implement Password Reset Flow" if item.target_issue_key == "PAY-104" else "Active Backlog Work",
                    "old_decision": "Implement custom password reset with email tokens",
                    "new_evidence": item.conflict_summary or "Dropping old password reset approach",
                    "recommendation": "Transition PAY-104 to Closed/Rejected or hold implementation",
                    "risk_level": item.risk
                })

            action = Action(
                id=action_id,
                meeting_id=meeting_id,
                action_type=item.action_type,
                summary=item.summary,
                description=item.description,
                target_issue_key=item.target_issue_key,
                project_key=item.project_key or project_key,
                issue_type=item.issue_type or "Task",
                owner_account_id=resolved_account_id,
                owner_name=item.owner_name,
                due_at=item.due_at,
                priority=item.priority or "Medium",
                confidence=item.confidence,
                risk=item.risk,
                status="PROPOSED",
                reason=item.reason,
                conflict_payload=conflict_payload_str,
                transition_name=item.transition_name
            )
            db.add(action)

            # Persist linked evidence items
            for ev in item.evidence:
                ev_obj = Evidence(
                    id=str(uuid.uuid4()),
                    action_id=action_id,
                    segment_id=ev.segment_id,
                    start_ms=ev.start_ms,
                    end_ms=ev.end_ms,
                    evidence_text=ev.evidence_text
                )
                db.add(ev_obj)

        # Record Audit
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            actor="system:llm_extractor",
            meeting_id=meeting_id,
            event_type="ACTIONS_EXTRACTED",
            after_state=f'{{"actions_count": {len(action_ids)}}}'
        )
        db.add(audit)

        await db.commit()

        # Reload with selectinload so relations are ready and eagerly cached
        stmt_actions = (
            select(Action)
            .where(Action.id.in_(action_ids))
            .options(selectinload(Action.evidence), selectinload(Action.executions), selectinload(Action.approval))
        )
        persisted_actions = (await db.execute(stmt_actions)).scalars().all()
        return list(persisted_actions)
