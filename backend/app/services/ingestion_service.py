from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment
from app.models.audit import AuditEvent
from app.schemas.meeting import TranscriptIngestRequest, SegmentInput
from app.utils.hashing import compute_transcript_hash
from app.utils.text_norm import parse_raw_transcript_text


class IngestionService:
    @staticmethod
    async def ingest_transcript(
        db: AsyncSession,
        request: TranscriptIngestRequest
    ) -> Meeting:
        """
        Normalizes transcript segments, generates idempotency SHA-256 hash,
        and saves meeting & transcript segments.
        """
        raw_segments: List[Dict[str, Any]] = []

        # 1. Process provided structured segments or parse raw text
        if request.segments and len(request.segments) > 0:
            for s in request.segments:
                raw_segments.append(s.model_dump())
        elif request.raw_text:
            raw_segments = parse_raw_transcript_text(request.raw_text)
        else:
            raw_segments = []

        # 2. Assign deterministic segment IDs and normalize
        normalized_segments: List[Dict[str, Any]] = []
        for i, s in enumerate(raw_segments):
            seg_id = s.get("id") or f"seg_{i+1:03d}"
            normalized_segments.append({
                "id": seg_id,
                "speaker_id": s.get("speaker_id") or f"spk_{s.get('speaker_name', 'user').lower().replace(' ', '_')}",
                "speaker_name": s.get("speaker_name", "Unknown").strip(),
                "start_ms": int(s.get("start_ms", 0)),
                "end_ms": int(s.get("end_ms", 0)),
                "text": s.get("text", "").strip()
            })

        # 3. Compute transcript SHA-256 hash for deduplication/idempotency
        t_hash = compute_transcript_hash(normalized_segments)

        # Check if identical transcript was already processed
        stmt = select(Meeting).where(Meeting.transcript_hash == t_hash)
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            return existing

        # 4. Create new Meeting entity
        meeting_id = str(uuid.uuid4())
        meeting = Meeting(
            id=meeting_id,
            title=request.title or "Engineering Sync",
            provider=request.provider or "manual",
            external_id=request.external_id,
            started_at=datetime.utcnow(),
            transcript_hash=t_hash,
            status="IN_PROGRESS"
        )
        db.add(meeting)

        # 5. Add Segments
        for s in normalized_segments:
            seg = TranscriptSegment(
                id=s["id"],
                meeting_id=meeting_id,
                speaker_id=s["speaker_id"],
                speaker_name=s["speaker_name"],
                start_ms=s["start_ms"],
                end_ms=s["end_ms"],
                text=s["text"]
            )
            db.add(seg)

        # 6. Record Audit Event
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            actor="system:ingestion",
            meeting_id=meeting_id,
            event_type="TRANSCRIPT_INGESTED",
            after_state=f'{{"segment_count": {len(normalized_segments)}, "hash": "{t_hash}"}}'
        )
        db.add(audit)

        await db.commit()
        await db.refresh(meeting)
        return meeting
