"""Connector-agnostic workflow item refactor

Adds ``item_type`` / ``target_connector`` to ``actions``, introduces the
``jira_action_details`` (1:1) and ``task_dependencies`` tables, and backfills
existing rows without dropping any data (blueprint Sections 11 & 12).

Revision ID: 0001_workflow_item
Revises:
Create Date: 2026-08-28
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "0001_workflow_item"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table: str) -> set:
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # This project bootstraps its base schema via SQLAlchemy ``create_all`` on app
    # startup, not migrations. If this migration runs first against a brand-new
    # database, create the base tables so the additive steps below have something
    # to attach to. On an existing ocra.db this is a no-op (tables already there).
    if "actions" not in tables:
        from app.database import Base
        import app.models  # noqa: F401  (populate Base.metadata)

        Base.metadata.create_all(bind=bind)
        inspector = sa.inspect(bind)
        tables = set(inspector.get_table_names())

    # --- 1. Additive columns on `actions` -------------------------------------
    action_cols = _columns(inspector, "actions") if "actions" in tables else set()

    with op.batch_alter_table("actions") as batch:
        if "item_type" not in action_cols:
            batch.add_column(
                sa.Column("item_type", sa.String(length=20), nullable=False, server_default="TASK")
            )
        if "target_connector" not in action_cols:
            batch.add_column(
                sa.Column(
                    "target_connector", sa.String(length=30), nullable=False, server_default="jira"
                )
            )

    # Explicit backfill for any pre-existing rows (server_default also covers this
    # on SQLite, but we make the intent unambiguous and portable).
    op.execute(
        "UPDATE actions SET item_type = 'TASK' "
        "WHERE item_type IS NULL OR item_type = ''"
    )
    op.execute(
        "UPDATE actions SET target_connector = 'jira' "
        "WHERE target_connector IS NULL OR target_connector = ''"
    )

    # --- 2. jira_action_details (1:1 connector detail) -----------------------
    if "jira_action_details" not in tables:
        op.create_table(
            "jira_action_details",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "action_id",
                sa.String(length=36),
                sa.ForeignKey("actions.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("target_issue_key", sa.String(length=50), nullable=True),
            sa.Column("project_key", sa.String(length=20), nullable=True),
            sa.Column("issue_type", sa.String(length=50), nullable=True),
            sa.Column("transition_name", sa.String(length=100), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
        )
        op.create_index(
            "ix_jira_action_details_action_id", "jira_action_details", ["action_id"]
        )
        op.create_index(
            "ix_jira_action_details_target_issue_key",
            "jira_action_details",
            ["target_issue_key"],
        )

    # --- 3. task_dependencies (workflow graph edges) -----------------------
    if "task_dependencies" not in tables:
        op.create_table(
            "task_dependencies",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "task_id",
                sa.String(length=36),
                sa.ForeignKey("actions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "depends_on_task_id",
                sa.String(length=36),
                sa.ForeignKey("actions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "dependency_type",
                sa.String(length=30),
                nullable=False,
                server_default="blocks",
            ),
            sa.Column(
                "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
        )
        op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])
        op.create_index(
            "ix_task_dependencies_depends_on_task_id",
            "task_dependencies",
            ["depends_on_task_id"],
        )

    # --- 4. Backfill a jira_action_details row for every legacy action -------
    legacy_rows = bind.execute(
        sa.text(
            "SELECT a.id, a.target_issue_key, a.project_key, a.issue_type, a.transition_name "
            "FROM actions a "
            "LEFT JOIN jira_action_details d ON d.action_id = a.id "
            "WHERE d.id IS NULL"
        )
    ).fetchall()

    for row in legacy_rows:
        bind.execute(
            sa.text(
                "INSERT INTO jira_action_details "
                "(id, action_id, target_issue_key, project_key, issue_type, transition_name, created_at) "
                "VALUES (:id, :action_id, :tik, :pk, :it, :tn, CURRENT_TIMESTAMP)"
            ),
            {
                "id": str(uuid.uuid4()),
                "action_id": row[0],
                "tik": row[1],
                "pk": row[2],
                "it": row[3],
                "tn": row[4],
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "task_dependencies" in tables:
        op.drop_table("task_dependencies")
    if "jira_action_details" in tables:
        op.drop_table("jira_action_details")

    action_cols = _columns(inspector, "actions") if "actions" in tables else set()
    with op.batch_alter_table("actions") as batch:
        if "target_connector" in action_cols:
            batch.drop_column("target_connector")
        if "item_type" in action_cols:
            batch.drop_column("item_type")
