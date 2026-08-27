"""Tests for the connector-agnostic Workflow Item refactor (blueprint Sections 11 & 12).

Covers:
  * TaskDependency rows are created from extraction output.
  * The Alembic backfill migration preserves existing `actions` data.
  * `item_type` defaults to 'TASK' for legacy rows.
"""
import os
import sqlite3
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models.meeting import Meeting
from app.models.transcript_segment import TranscriptSegment
from app.models.action import Action, JiraActionDetail, TaskDependency
from app.services.extraction_service import ExtractionService

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


# --------------------------------------------------------------------------- #
# 1. Dependency graph is populated from extraction                            #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_extraction_creates_task_dependency_rows(test_db: AsyncSession):
    meeting = Meeting(id="meet_dep_1", title="Auth Roadmap Sync")
    test_db.add(meeting)
    test_db.add_all([
        TranscriptSegment(
            id="seg_a", meeting_id="meet_dep_1", speaker_name="Rahul",
            start_ms=0, end_ms=4000,
            text="Rahul will implement the OAuth backend by Friday.",
        ),
        TranscriptSegment(
            id="seg_b", meeting_id="meet_dep_1", speaker_name="Priya",
            start_ms=5000, end_ms=9000,
            text="Priya will add the login UI once the backend is ready.",
        ),
    ])
    await test_db.commit()

    actions = await ExtractionService.extract_meeting_actions(test_db, "meet_dep_1", project_key="PAY")
    oauth = next(a for a in actions if "OAuth" in a.summary)
    login = next(a for a in actions if "Login UI" in a.summary)

    edges = (await test_db.execute(select(TaskDependency))).scalars().all()
    assert len(edges) == 1
    edge = edges[0]
    assert edge.task_id == login.id
    assert edge.depends_on_task_id == oauth.id
    assert edge.dependency_type == "blocks"

    # Relationship wiring: dependencies (this -> depends_on) and dependents (other -> this).
    await test_db.refresh(login, ["dependencies"])
    await test_db.refresh(oauth, ["dependents"])
    assert [d.depends_on_task_id for d in login.dependencies] == [oauth.id]
    assert [d.task_id for d in oauth.dependents] == [login.id]

    # Unresolved / duplicate references must not create spurious edges.
    assert all(e.task_id != e.depends_on_task_id for e in edges)


@pytest.mark.asyncio
async def test_extraction_sets_item_type_and_connector_and_jira_detail(test_db: AsyncSession):
    meeting = Meeting(id="meet_dep_2", title="Sync")
    test_db.add(meeting)
    test_db.add(TranscriptSegment(
        id="seg_c", meeting_id="meet_dep_2", speaker_name="Rahul",
        start_ms=0, end_ms=4000,
        text="Rahul will implement the OAuth backend by Friday.",
    ))
    await test_db.commit()

    actions = await ExtractionService.extract_meeting_actions(test_db, "meet_dep_2", project_key="PAY")
    assert actions
    for a in actions:
        assert a.item_type in ("TASK", "DECISION", "EVENT", "DEPENDENCY", "RISK", "QUESTION")
        assert a.target_connector == "jira"
        # 1:1 connector detail mirrors the legacy Jira columns.
        assert a.jira_detail is not None
        assert a.jira_detail.project_key == a.project_key
        assert a.jira_detail.issue_type == a.issue_type


# --------------------------------------------------------------------------- #
# 2. Alembic backfill migration preserves existing data                      #
# --------------------------------------------------------------------------- #
def _build_legacy_db(path: str) -> list:
    """Create a pre-refactor schema (no item_type / no new tables) and seed rows."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE meetings (id VARCHAR(36) PRIMARY KEY, title VARCHAR(255));
        CREATE TABLE actions (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            meeting_id VARCHAR(36) NOT NULL,
            action_type VARCHAR(30) NOT NULL,
            summary VARCHAR(500) NOT NULL,
            description TEXT,
            target_issue_key VARCHAR(50),
            project_key VARCHAR(20) NOT NULL,
            issue_type VARCHAR(50) NOT NULL,
            owner_account_id VARCHAR(100),
            owner_name VARCHAR(100),
            due_at VARCHAR(50),
            priority VARCHAR(30),
            confidence FLOAT NOT NULL,
            risk VARCHAR(20) NOT NULL,
            status VARCHAR(30) NOT NULL,
            reason TEXT NOT NULL,
            conflict_payload TEXT,
            transition_name VARCHAR(100),
            created_at DATETIME NOT NULL
        );
        """
    )
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    conn.execute("INSERT INTO meetings (id, title) VALUES ('m1', 'Legacy Meeting')")
    conn.execute(
        "INSERT INTO actions (id, meeting_id, action_type, summary, project_key, issue_type, "
        "confidence, risk, status, reason, target_issue_key, transition_name, created_at) "
        "VALUES (?, 'm1', 'CREATE', 'Legacy task one', 'PAY', 'Task', 0.9, 'LOW', 'PROPOSED', "
        "'seed', NULL, NULL, CURRENT_TIMESTAMP)",
        (ids[0],),
    )
    conn.execute(
        "INSERT INTO actions (id, meeting_id, action_type, summary, project_key, issue_type, "
        "confidence, risk, status, reason, target_issue_key, transition_name, created_at) "
        "VALUES (?, 'm1', 'TRANSITION', 'Legacy task two', 'ENG', 'Bug', 0.8, 'MEDIUM', 'APPROVED', "
        "'seed', 'ENG-42', 'Done', CURRENT_TIMESTAMP)",
        (ids[1],),
    )
    conn.commit()
    conn.close()
    return ids


def _run_alembic_upgrade(db_path: str):
    from alembic.config import Config
    from alembic import command

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    os.environ["ALEMBIC_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    try:
        command.upgrade(cfg, "head")
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL", None)


def test_backfill_migration_preserves_legacy_actions(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    ids = _build_legacy_db(db_path)

    _run_alembic_upgrade(db_path)

    conn = sqlite3.connect(db_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(actions)")}
        assert {"item_type", "target_connector"} <= cols

        rows = conn.execute(
            "SELECT id, summary, project_key, issue_type, item_type, target_connector "
            "FROM actions"
        ).fetchall()
        by_summary = {r[1]: r for r in rows}
        # No rows dropped, original values intact.
        assert set(by_summary) == {"Legacy task one", "Legacy task two"}
        assert {r[0] for r in rows} == set(ids)
        assert by_summary["Legacy task one"][2] == "PAY"
        assert by_summary["Legacy task one"][3] == "Task"
        assert by_summary["Legacy task two"][2] == "ENG"
        assert by_summary["Legacy task two"][3] == "Bug"

        # Backfill: every legacy row is TASK / jira.
        assert all(r[4] == "TASK" for r in rows)
        assert all(r[5] == "jira" for r in rows)

        # 1:1 jira_action_details backfilled from the legacy Jira columns.
        details = conn.execute(
            "SELECT action_id, target_issue_key, project_key, issue_type, transition_name "
            "FROM jira_action_details ORDER BY project_key"
        ).fetchall()
        assert len(details) == 2
        detail_by_action = {d[0]: d for d in details}
        assert set(detail_by_action) == set(ids)
        eng_detail = next(d for d in details if d[2] == "ENG")
        assert eng_detail[1] == "ENG-42"
        assert eng_detail[4] == "Done"

        # task_dependencies table exists and starts empty.
        assert conn.execute("SELECT COUNT(*) FROM task_dependencies").fetchone()[0] == 0
    finally:
        conn.close()


def test_backfill_migration_is_idempotent(tmp_path):
    db_path = str(tmp_path / "legacy2.db")
    _build_legacy_db(db_path)
    _run_alembic_upgrade(db_path)
    # Re-running to head is a no-op (already at head); downgrade+upgrade round-trips cleanly.
    from alembic.config import Config
    from alembic import command

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    os.environ["ALEMBIC_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    try:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL", None)

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM jira_action_details").fetchone()[0] == 2
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# 3. item_type defaults to TASK for rows inserted without it                  #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_item_type_defaults_to_task_for_legacy_insert(test_db: AsyncSession):
    # Simulate a legacy writer that does not know about item_type / target_connector.
    test_db.add(Meeting(id="m_leg", title="x"))
    await test_db.commit()
    await test_db.execute(text(
        "INSERT INTO actions (id, meeting_id, action_type, summary, project_key, issue_type, "
        "confidence, risk, status, reason, created_at) "
        "VALUES ('a_leg', 'm_leg', 'CREATE', 'no item_type set', 'PAY', 'Task', "
        "0.9, 'LOW', 'PROPOSED', 'seed', CURRENT_TIMESTAMP)"
    ))
    await test_db.commit()

    row = (await test_db.execute(select(Action).where(Action.id == "a_leg"))).scalars().one()
    assert row.item_type == "TASK"
    assert row.target_connector == "jira"
