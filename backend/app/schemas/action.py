from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class EvidenceRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    segment_id: str
    start_ms: int = 0
    end_ms: int = 0
    evidence_text: str


class ConflictDetails(BaseModel):
    affected_issue_key: str
    affected_issue_summary: str
    old_decision: str
    new_evidence: str
    recommendation: str
    risk_level: str = "HIGH"


class ActionBase(BaseModel):
    action_type: str  # CREATE, UPDATE, ASSIGN, COMMENT, SHIFT_DEADLINE, TRANSITION, CONFLICT, NO_ACTION
    summary: str
    description: Optional[str] = None
    target_issue_key: Optional[str] = None
    project_key: str = "PAY"
    issue_type: str = "Task"
    owner_account_id: Optional[str] = None
    owner_name: Optional[str] = None
    due_at: Optional[str] = None
    priority: Optional[str] = "Medium"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    risk: str = "LOW"  # LOW, MEDIUM, HIGH
    status: str = "PROPOSED"
    reason: str
    conflict_payload: Optional[str] = None
    transition_name: Optional[str] = None


class ActionCreate(ActionBase):
    meeting_id: str
    evidence: List[EvidenceRef] = []


class ApprovalInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    required: bool
    reviewer: Optional[str] = None
    decision: str
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None


class ExecutionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation: str
    idempotency_key: str
    status: str
    jira_issue_key: Optional[str] = None
    jira_response_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    executed_at: datetime


class ActionResponse(ActionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    created_at: datetime
    evidence: List[EvidenceRef] = []
    executions: List[ExecutionInfo] = []
    approval: Optional[ApprovalInfo] = None
    conflict_info: Optional[ConflictDetails] = None


class ApproveRejectRequest(BaseModel):
    reviewer: Optional[str] = "Engineering Lead"
    comment: Optional[str] = None
