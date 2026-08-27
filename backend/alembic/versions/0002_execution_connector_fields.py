"""Per-connector execution fields

Adds ``executions.target_connector`` (default 'jira') and ``executions.external_url``
so per-action partial success/failure can be reported per connector
(blueprint Sections 15 & 18). Non-destructive / additive.

Revision ID: 0002_exec_connector
Revises: 0001_workflow_item
Create Date: 2026-08-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_exec_connector"
down_revision: Union[str, None] = "0001_workflow_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table: str) -> set:
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "executions" not in set(inspector.get_table_names()):
        # Fresh DB bootstrapped elsewhere (create_all) — nothing to alter.
        return

    cols = _columns(inspector, "executions")
    with op.batch_alter_table("executions") as batch:
        if "target_connector" not in cols:
            batch.add_column(
                sa.Column(
                    "target_connector",
                    sa.String(length=30),
                    nullable=False,
                    server_default="jira",
                )
            )
        if "external_url" not in cols:
            batch.add_column(sa.Column("external_url", sa.String(length=500), nullable=True))

    op.execute(
        "UPDATE executions SET target_connector = 'jira' "
        "WHERE target_connector IS NULL OR target_connector = ''"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "executions" not in set(inspector.get_table_names()):
        return
    cols = _columns(inspector, "executions")
    with op.batch_alter_table("executions") as batch:
        if "external_url" in cols:
            batch.drop_column("external_url")
        if "target_connector" in cols:
            batch.drop_column("target_connector")
