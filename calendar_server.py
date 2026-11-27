"""Google Calendar MCP server (real Google Calendar API).

Runs as a stdio subprocess started by host.py. Never print to stdout here:
stdout carries the MCP protocol. Use stderr for logs.
Run `python auth_google.py` once beforehand to create token.json.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = Path(__file__).parent
TOKEN_FILE = BASE / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TZ_NAME = "Asia/Kolkata"  # change if your phone calendar uses another timezone
TZ = ZoneInfo(TZ_NAME)

mcp = FastMCP(name="GoogleCalendar")
_events_api = None


def _log(msg: str) -> None:
    print(f"[calendar-mcp] {msg}", file=sys.stderr, flush=True)


def _events():
    """Lazily build the Calendar client. Expired access tokens refresh automatically."""
    global _events_api
    if _events_api is None:
        if not TOKEN_FILE.exists():
            raise RuntimeError("token.json not found. Run `python auth_google.py` first.")
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        _events_api = build("calendar", "v3", credentials=creds, cache_discovery=False).events()
    return _events_api


def _fmt(e: dict) -> dict:
    return {
        "id": e["id"],
        "title": e.get("summary", "(no title)"),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "end": e["end"].get("dateTime", e["end"].get("date")),
        "notes": e.get("description", ""),
    }


@mcp.tool()
def create_event(title: str, date: str, time: str, duration_minutes: int = 60, notes: str = "") -> str:
    """Create a calendar event.
    Args:
        title: Name of the event (e.g. 'Team sync').
        date: Date in YYYY-MM-DD format.
        time: Start time in HH:MM format (24-hour).
        duration_minutes: Length of the event in minutes (default 60).
        notes: Optional description or location.
    """
    _log(f"create_event({title!r}, {date}, {time}, {duration_minutes}m)")
    start = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=TZ)
    end = start + timedelta(minutes=duration_minutes)
    body = {
        "summary": title,
        "description": notes,
        "start": {"dateTime": start.isoformat(), "timeZone": TZ_NAME},
        "end": {"dateTime": end.isoformat(), "timeZone": TZ_NAME},
    }
    ev = _events().insert(calendarId="primary", body=body).execute()
    return f"Created '{title}' on {date} at {time} for {duration_minutes} min (id: {ev['id']})."


@mcp.tool()
def list_events(date: str = "") -> list[dict]:
    """List calendar events. Pass a date (YYYY-MM-DD) for that day only;
    leave empty for the next upcoming events. Each result includes the event id."""
    _log(f"list_events({date!r})")
    kwargs = {}
    if date:
        day = datetime.fromisoformat(date).replace(tzinfo=TZ)
        kwargs["timeMin"] = day.isoformat()
        kwargs["timeMax"] = (day + timedelta(days=1)).isoformat()
    else:
        kwargs["timeMin"] = datetime.now(TZ).isoformat()
    items = _events().list(
        calendarId="primary", singleEvents=True, orderBy="startTime", maxResults=15, **kwargs
    ).execute().get("items", [])
    return [_fmt(e) for e in items]


@mcp.tool()
def update_event(event_id: str, title: str = "", date: str = "", time: str = "", duration_minutes: int = 0) -> str:
    """Reschedule or rename an existing event. Only pass the fields that change.
    Args:
        event_id: The id from list_events.
        title: New title (optional).
        date: New date YYYY-MM-DD (optional).
        time: New start time HH:MM, 24-hour (optional). Duration is kept unless changed.
        duration_minutes: New duration in minutes (optional).
    """
    _log(f"update_event({event_id}, title={title!r}, date={date!r}, time={time!r}, dur={duration_minutes})")
    ev = _events().get(calendarId="primary", eventId=event_id).execute()
    if "dateTime" not in ev["start"]:
        return "That is an all-day event; I can only reschedule timed events."
    start = datetime.fromisoformat(ev["start"]["dateTime"]).astimezone(TZ)
    end = datetime.fromisoformat(ev["end"]["dateTime"]).astimezone(TZ)
    length = end - start
    if date or time:
        new_date = date or start.date().isoformat()
        new_time = time or start.strftime("%H:%M")
        start = datetime.fromisoformat(f"{new_date}T{new_time}").replace(tzinfo=TZ)
    end = start + (timedelta(minutes=duration_minutes) if duration_minutes else length)
    patch = {
        "start": {"dateTime": start.isoformat(), "timeZone": TZ_NAME},
        "end": {"dateTime": end.isoformat(), "timeZone": TZ_NAME},
    }
    if title:
        patch["summary"] = title
    _events().patch(calendarId="primary", eventId=event_id, body=patch).execute()
    return f"Updated '{title or ev.get('summary', 'event')}' to {start.strftime('%Y-%m-%d %H:%M')}."


@mcp.tool()
def delete_event(event_id: str) -> str:
    """Delete a calendar event by its id (get the id from list_events first)."""
    _log(f"delete_event({event_id})")
    _events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Deleted event {event_id}."


if __name__ == "__main__":
    mcp.run()