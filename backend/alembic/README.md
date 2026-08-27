# Database migrations (Alembic)

The base schema is still created by SQLAlchemy `create_all` on app startup
(`app.database.init_db`). Alembic manages *deltas* on top of that.

## Run

```bash
# uses app.config.settings.DATABASE_URL (override with DATABASE_URL / ALEMBIC_DATABASE_URL)
python -m alembic upgrade head
python -m alembic downgrade -1
```

The async driver suffix (`+aiosqlite` / `+asyncpg`) is stripped automatically in
`env.py` so migrations run on a sync engine.

## Revisions

| Revision            | Summary |
|---------------------|---------|
| `0001_workflow_item` | Connector-agnostic Workflow Item refactor: adds `actions.item_type` / `actions.target_connector`, the `jira_action_details` (1:1) and `task_dependencies` tables, and backfills existing rows (`item_type='TASK'`, `target_connector='jira'`, one `jira_action_details` row per legacy action). Non-destructive. |
| `0002_exec_connector` | Adds `executions.target_connector` (default `'jira'`) and `executions.external_url` so per-action partial success/failure is tracked per connector (Jira / GitHub / Google Calendar). Non-destructive. |
