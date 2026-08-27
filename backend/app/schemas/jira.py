from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class JiraUser(BaseModel):
    account_id: str
    display_name: str
    email: Optional[str] = None
    active: bool = True
    avatar_url: Optional[str] = None


class JiraTransition(BaseModel):
    id: str
    name: str
    to_status: str


class JiraComment(BaseModel):
    id: str
    author: str
    body: str
    created: datetime


class JiraIssue(BaseModel):
    id: str
    key: str
    summary: str
    description: Optional[str] = None
    status: str = "To Do"
    issue_type: str = "Task"
    assignee: Optional[JiraUser] = None
    priority: str = "Medium"
    due_date: Optional[str] = None
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    comments: List[JiraComment] = []


class JiraProject(BaseModel):
    id: str
    key: str
    name: str
    issue_types: List[str] = ["Task", "Story", "Bug", "Epic"]


class JiraConfigUpdate(BaseModel):
    project_key: Optional[str] = None
    auto_execute_enabled: Optional[bool] = None
    min_confidence_threshold: Optional[float] = None
    kill_switch_active: Optional[bool] = None
    allowed_transitions: Optional[List[str]] = None


class JiraConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_key: str
    project_name: str
    auto_execute_enabled: bool
    min_confidence_threshold: float
    kill_switch_active: bool
    allowed_transitions: List[str]
    created_at: datetime
    updated_at: datetime
