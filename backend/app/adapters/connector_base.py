"""Connector abstraction (blueprint Section 15 "Connector Architecture").

Python translation of the TypeScript interfaces in the blueprint:

    interface TaskConnector {
      createTask(task: WorkflowTask): Promise<ConnectorResult>;
      updateTask(id: string, task: WorkflowTask): Promise<ConnectorResult>;
      deleteTask(id: string): Promise<ConnectorResult>;
    }

    interface CalendarConnector {
      createEvent(event: WorkflowEvent): Promise<ConnectorResult>;
      updateEvent(id: string, event: WorkflowEvent): Promise<ConnectorResult>;
    }

The reasoning/execution layers only ever speak this contract. Each connector
translates the normalized :class:`WorkflowItemPayload` into its own vendor schema
(blueprint Section 12: "decouple AI output from any vendor-specific API").
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConnectorResult(BaseModel):
    """Uniform outcome of a single connector operation.

    Enables per-action partial success / failure reporting (blueprint Section 18)
    instead of failing an entire workflow when one connector errors.
    """

    success: bool
    external_id: Optional[str] = None       # vendor primary id (Jira issue id, GH node/number, GCal event id)
    external_url: Optional[str] = None      # human-openable link to the created/updated object
    error: Optional[str] = None             # human-readable error message when success is False

    # Convenience extras (not part of the blueprint's 4 fields, but useful downstream).
    external_key: Optional[str] = None      # e.g. Jira "PAY-105" or GitHub issue number as string
    connector: Optional[str] = None         # "jira" | "github" | "google_calendar"
    raw: Optional[Dict[str, Any]] = None    # raw vendor payload for auditing

    @classmethod
    def ok(cls, **kwargs: Any) -> "ConnectorResult":
        return cls(success=True, **kwargs)

    @classmethod
    def fail(cls, error: str, connector: Optional[str] = None, **kwargs: Any) -> "ConnectorResult":
        return cls(success=False, error=error, connector=connector, **kwargs)


class WorkflowItemPayload(BaseModel):
    """Normalized, connector-agnostic representation of a workflow item.

    Mirrors the blueprint's ``WorkflowTask`` envelope (Section 12) plus the
    calendar-event fields needed by :class:`CalendarConnector`.
    """

    # Identity / traceability
    source_action_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    item_type: str = "TASK"                 # TASK | DECISION | EVENT | DEPENDENCY | RISK | QUESTION

    # Task-ish fields
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None          # login / email / account id — connector resolves
    priority: Optional[str] = "Medium"
    due_at: Optional[str] = None            # ISO date "2026-08-28"
    labels: List[str] = Field(default_factory=list)

    # Event-ish fields (CalendarConnector)
    start_time: Optional[str] = None        # ISO-8601 datetime
    end_time: Optional[str] = None

    # Context for rich descriptions
    meeting_title: Optional[str] = None
    reason: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

    # Free-form extras (target repo, calendar id, etc.)
    extra: Dict[str, Any] = Field(default_factory=dict)


class TaskConnector(ABC):
    """Contract for systems that hold *tasks* (Jira, GitHub Issues, Asana, ...)."""

    #: stable registry name, e.g. "jira" / "github"
    connector_name: str = "task"

    @abstractmethod
    async def create_task(self, item: WorkflowItemPayload) -> ConnectorResult:
        ...

    @abstractmethod
    async def update_task(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        ...

    @abstractmethod
    async def delete_task(self, external_id: str) -> ConnectorResult:
        ...


class CalendarConnector(ABC):
    """Contract for systems that hold *time-bound events* (Google Calendar, Outlook, ...)."""

    connector_name: str = "calendar"

    @abstractmethod
    async def create_event(self, item: WorkflowItemPayload) -> ConnectorResult:
        ...

    @abstractmethod
    async def update_event(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        ...
