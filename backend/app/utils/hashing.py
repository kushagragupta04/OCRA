import hashlib
import json
from typing import Any, Dict


def compute_transcript_hash(segments: list[Dict[str, Any]]) -> str:
    """
    Computes a deterministic SHA-256 hash over normalized transcript segments.
    """
    normalized_repr = []
    for s in sorted(segments, key=lambda x: (x.get("start_ms", 0), x.get("speaker_name", ""))):
        normalized_repr.append({
            "speaker": s.get("speaker_name", "").strip().lower(),
            "start": s.get("start_ms", 0),
            "end": s.get("end_ms", 0),
            "text": " ".join(s.get("text", "").split()).strip()
        })
    
    dumped = json.dumps(normalized_repr, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def compute_idempotency_key(meeting_id: str, action_fingerprint: str, operation: str) -> str:
    """
    Generates unique idempotency key for Jira mutation.
    """
    raw = f"{meeting_id}:{action_fingerprint}:{operation}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
