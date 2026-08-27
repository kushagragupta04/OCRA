from sqlalchemy import Column, String, Float, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


# Allowed connector-agnostic workflow item types (blueprint Section 13.1).
ITEM_TYPES = ("TASK", "DECISION", "EVENT", "DEPENDENCY", "RISK", "QUESTION")


class Action(Base):
    """
    Normalized Workflow Item (blueprint Section 12).

    Historically this model was Jira-specific. It is now the connector-agnostic
    "Workflow Object": ``item_type`` classifies it, ``target_connector`` routes it,
    and vendor-specific fields live in the related :class:`JiraActionDetail` row.
    The legacy Jira columns (``target_issue_key`` / ``project_key`` / ``issue_type``
    / ``transition_name``) are retained as-is for backward compatibility with the
    existing Jira execution path and are mirrored into ``jira_detail``.
    """

    __tablename__ = "actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(30), nullable=False)  # CREATE, UPDATE, ASSIGN, COMMENT, SHIFT_DEADLINE, TRANSITION, CONFLICT, NO_ACTION

    # --- Connector-agnostic classification / routing (blueprint Section 12/13.1) ---
    item_type = Column(
        String(20), nullable=False, default="TASK", server_default="TASK"
    )  # TASK | DECISION | EVENT | DEPENDENCY | RISK | QUESTION
    target_connector = Column(
        String(30), nullable=False, default="jira", server_default="jira"
    )  # jira | github | google_calendar | ...

    summary = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # --- Legacy Jira-specific columns (kept for backward compatibility) ---
    target_issue_key = Column(String(50), nullable=True, index=True)
    project_key = Column(String(20), nullable=False, default="PAY")
    issue_type = Column(String(50), nullable=False, default="Task")
    transition_name = Column(String(100), nullable=True)

    owner_account_id = Column(String(100), nullable=True)
    owner_name = Column(String(100), nullable=True)
    due_at = Column(String(50), nullable=True)
    priority = Column(String(30), nullable=True, default="Medium")
    confidence = Column(Float, nullable=False, default=1.0)
    risk = Column(String(20), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH
    status = Column(String(30), nullable=False, default="PROPOSED")  # PROPOSED, AUTO_EXECUTED, REQUIRES_APPROVAL, APPROVED, REJECTED, EXECUTING, COMPLETED, FAILED
    reason = Column(Text, nullable=False)
    conflict_payload = Column(Text, nullable=True)  # JSON string for contradiction / scope diff
    created_at = Column(DateTime, nullable=False, default=func.now())

    meeting = relationship("Meeting", back_populates="actions")
    evidence = relationship("Evidence", back_populates="action", cascade="all, delete-orphan", lazy="selectin")
    executions = relationship("Execution", back_populates="action", cascade="all, delete-orphan", lazy="selectin")
    approval = relationship("Approval", back_populates="action", uselist=False, cascade="all, delete-orphan", lazy="selectin")

    # 1:1 connector-specific detail (Jira). New vendors get their own detail table.
    jira_detail = relationship(
        "JiraActionDetail",
        back_populates="action",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Workflow graph edges (blueprint Section 11 "TaskDependency").
    # ``dependencies``: rows where this item is the dependent (this -> depends_on).
    # ``dependents``:  rows where this item is depended upon (other -> this).
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JiraActionDetail(Base):
    """Vendor-specific (Jira) fields for a workflow item, referenced 1:1 from :class:`Action`."""

    __tablename__ = "jira_action_details"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(
        String(36),
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    target_issue_key = Column(String(50), nullable=True, index=True)
    project_key = Column(String(20), nullable=True)
    issue_type = Column(String(50), nullable=True)
    transition_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    action = relationship("Action", back_populates="jira_detail")


class TaskDependency(Base):
    """Directed workflow-graph edge: ``task_id`` depends on ``depends_on_task_id``."""

    __tablename__ = "task_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(
        String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    depends_on_task_id = Column(
        String(36), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependency_type = Column(String(30), nullable=False, default="blocks", server_default="blocks")
    created_at = Column(DateTime, nullable=False, default=func.now())

    task = relationship("Action", foreign_keys=[task_id], back_populates="dependencies")
    depends_on = relationship("Action", foreign_keys=[depends_on_task_id], back_populates="dependents")
