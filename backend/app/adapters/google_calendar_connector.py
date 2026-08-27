"""Google Calendar connector (blueprint Section 15.1 — "Google Calendar").

Implements :class:`CalendarConnector` against the Google Calendar API
(``events.insert`` / ``events.patch``). Real mode uses an OAuth2 access token
obtained via the same 3LO pattern as Jira (see
``routers/integrations.py`` ``calendar_router``). A credential-free in-memory mock
mirrors :mod:`app.adapters.jira_mock_sandbox` for local dev / demo / tests.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.adapters.connector_base import (
    CalendarConnector,
    ConnectorResult,
    WorkflowItemPayload,
)


class CalendarEvent(BaseModel):
    id: str
    calendar_id: str = "primary"
    summary: str
    description: Optional[str] = None
    start: str                      # ISO-8601 datetime
    end: str
    attendees: List[str] = Field(default_factory=list)
    html_link: str = ""
    status: str = "confirmed"
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


def _derive_window(item: WorkflowItemPayload) -> tuple[str, str]:
    """Resolve (start, end) ISO strings from the payload with sane fallbacks."""
    start = item.start_time or item.due_at or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    if item.end_time:
        end = item.end_time
    else:
        try:
            base = datetime.fromisoformat(start.replace("Z", ""))
        except ValueError:
            base = datetime.utcnow()
        end = (base + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    return start, end


def _resolve_calendar_id(item: WorkflowItemPayload) -> str:
    return item.extra.get("calendar_id") or settings.GOOGLE_CALENDAR_ID or "primary"


# --------------------------------------------------------------------------- #
# Mock / sandbox                                                             #
# --------------------------------------------------------------------------- #
class GoogleCalendarMockAdapter(CalendarConnector):
    """In-memory Google Calendar simulator. Deterministic, zero-dependency."""

    connector_name = "google_calendar"

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._events: Dict[str, CalendarEvent] = {}
        self._counter = 0
        self._idem: Dict[str, str] = {}  # idempotency_key -> event id

    async def list_events(self, calendar_id: Optional[str] = None) -> List[CalendarEvent]:
        return [e for e in self._events.values() if calendar_id is None or e.calendar_id == calendar_id]

    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        return self._events.get(event_id)

    def _result_for(self, ev: CalendarEvent) -> ConnectorResult:
        return ConnectorResult.ok(
            connector="google_calendar",
            external_id=ev.id,
            external_key=ev.id,
            external_url=ev.html_link,
            raw=ev.model_dump(mode="json"),
        )

    async def create_event(self, item: WorkflowItemPayload) -> ConnectorResult:
        async with self._lock:
            key = item.idempotency_key
            if key and key in self._idem:
                return self._result_for(self._events[self._idem[key]])

            self._counter += 1
            event_id = f"evt_{self._counter:04d}"
            start, end = _derive_window(item)
            ev = CalendarEvent(
                id=event_id,
                calendar_id=_resolve_calendar_id(item),
                summary=item.title,
                description=item.description or item.reason,
                start=start,
                end=end,
                attendees=[item.assignee] if item.assignee else [],
                html_link=f"https://calendar.google.com/calendar/event?eid={event_id}",
            )
            self._events[event_id] = ev
            if key:
                self._idem[key] = event_id
            return self._result_for(ev)

    async def update_event(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        async with self._lock:
            ev = self._events.get(external_id)
            if not ev:
                return ConnectorResult.fail(f"Event '{external_id}' not found.", connector="google_calendar")
            ev.summary = item.title or ev.summary
            if item.description is not None:
                ev.description = item.description
            if item.start_time:
                ev.start = item.start_time
            if item.end_time:
                ev.end = item.end_time
            ev.updated = datetime.utcnow()
            return self._result_for(ev)

    def reset(self) -> None:
        self._events.clear()
        self._idem.clear()
        self._counter = 0


# --------------------------------------------------------------------------- #
# Real Google Calendar adapter                                               #
# --------------------------------------------------------------------------- #
class GoogleCalendarConnector(CalendarConnector):
    """Production Google Calendar adapter (OAuth2 bearer token)."""

    connector_name = "google_calendar"

    def __init__(self, access_token: Optional[str] = None, calendar_id: Optional[str] = None) -> None:
        self.access_token = access_token or settings.GOOGLE_OAUTH_ACCESS_TOKEN or ""
        self.calendar_id = calendar_id or settings.GOOGLE_CALENDAR_ID or "primary"
        self.base_url = settings.GOOGLE_CALENDAR_API_BASE.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.access_token:
            raise ValueError("GOOGLE_OAUTH_ACCESS_TOKEN is not configured.")
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=self._headers(), json=json_data)
        if resp.status_code in (401, 403):
            raise PermissionError(f"Google Calendar authorization failed: {resp.status_code} - {resp.text}")
        if resp.status_code >= 400:
            raise RuntimeError(f"Google Calendar API error {resp.status_code}: {resp.text}")
        return resp.json() if resp.text else {}

    def _event_body(self, item: WorkflowItemPayload) -> Dict[str, Any]:
        start, end = _derive_window(item)
        body: Dict[str, Any] = {
            "summary": item.title,
            "description": item.description or item.reason or "",
            "start": {"dateTime": start if "T" in start else f"{start}T09:00:00", "timeZone": "UTC"},
            "end": {"dateTime": end if "T" in end else f"{end}T10:00:00", "timeZone": "UTC"},
        }
        if item.assignee and "@" in item.assignee:
            body["attendees"] = [{"email": item.assignee}]
        return body

    async def create_event(self, item: WorkflowItemPayload) -> ConnectorResult:
        cal = _resolve_calendar_id(item)
        try:
            r = await self._request("POST", f"/calendars/{cal}/events", json_data=self._event_body(item))
            return ConnectorResult.ok(
                connector="google_calendar", external_id=r.get("id"), external_key=r.get("id"),
                external_url=r.get("htmlLink"), raw=r,
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector="google_calendar")

    async def update_event(self, external_id: str, item: WorkflowItemPayload) -> ConnectorResult:
        cal = _resolve_calendar_id(item)
        try:
            r = await self._request(
                "PATCH", f"/calendars/{cal}/events/{external_id}", json_data=self._event_body(item)
            )
            return ConnectorResult.ok(
                connector="google_calendar", external_id=r.get("id"), external_key=r.get("id"),
                external_url=r.get("htmlLink"), raw=r,
            )
        except Exception as e:  # noqa: BLE001
            return ConnectorResult.fail(str(e), connector="google_calendar")
