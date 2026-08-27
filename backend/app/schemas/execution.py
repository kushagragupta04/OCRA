from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.action import ActionResponse


class ExecutionPlanResponse(BaseModel):
    meeting_id: str
    total_actions: int
    auto_executable: List[ActionResponse] = []
    requires_approval: List[ActionResponse] = []
    conflicts: List[ActionResponse] = []
    executed: List[ActionResponse] = []
    policy_summary: dict


class BatchExecuteRequest(BaseModel):
    action_ids: List[str]
