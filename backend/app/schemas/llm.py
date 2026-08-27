from pydantic import BaseModel, Field
from typing import Optional, List


class LLMEvidenceItem(BaseModel):
    segment_id: str
    start_ms: int = 0
    end_ms: int = 0
    evidence_text: str


class LLMExtractedAction(BaseModel):
    action_type: str = Field(description="Action type: CREATE, UPDATE, ASSIGN, COMMENT, SHIFT_DEADLINE, TRANSITION, CONFLICT, or NO_ACTION")
    summary: str = Field(description="Clear, concise action summary")
    description: Optional[str] = Field(default=None, description="Detailed description or context")
    target_issue_key: Optional[str] = Field(default=None, description="Target Jira issue key if explicitly mentioned or referenced, e.g. PAY-104")
    project_key: Optional[str] = Field(default="PAY", description="Target Jira project key")
    issue_type: Optional[str] = Field(default="Task", description="Task, Bug, Story, Epic")
    owner_name: Optional[str] = Field(default=None, description="Explicit owner name mentioned in meeting")
    due_at: Optional[str] = Field(default=None, description="Explicit due date or relative timeframe mentioned, e.g. '2026-08-28' or 'by Friday'")
    priority: Optional[str] = Field(default="Medium", description="Explicit priority if discussed: Low, Medium, High, Highest")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Extraction confidence score from 0.0 to 1.0")
    risk: str = Field(default="LOW", description="Risk assessment: LOW, MEDIUM, HIGH")
    reason: str = Field(description="Why this action was extracted from the conversation")
    transition_name: Optional[str] = Field(default=None, description="Target workflow state if moving ticket")
    conflict_summary: Optional[str] = Field(default=None, description="If this decision drops, replaces, or contradicts prior work")
    evidence: List[LLMEvidenceItem] = Field(description="List of timestamped transcript segments supporting this action")


class LLMExtractionResponse(BaseModel):
    meeting_summary: Optional[str] = Field(default=None, description="High-level engineering meeting summary")
    actions: List[LLMExtractedAction] = Field(default=[], description="List of extracted evidence-backed Jira actions")
