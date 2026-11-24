import json
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP(name="GoogleCalendarMock")
DB_FILE = Path("calendar_db.json")


def _load_events() -> list[dict]:
    if not DB_FILE.exists():
        return []
    return json.loads(DB_FILE.read_text())


def _save_events(events: list[dict]) -> None:
    DB_FILE.write_text(json.dumps(events, indent=2))


@mcp.tool()
def create_event(title: str, date: str, time: str, notes: str = "") -> str:
    """Create a new calendar event.
    Args:
        title: Name of the event (e.g., 'Hackathon Sync').
        date: Date in YYYY-MM-DD format.
        time: Time in HH:MM format (24-hour).
        notes: Optional description or location.
    """
    events = _load_events()
    event = {
        "id": len(events) + 1,
        "title": title,
        "date": date,
        "time": time,
        "notes": notes,
    }
    events.append(event)
    _save_events(events)
    return f"Created event #{event['id']}: '{title}' on {date} at {time}."


@mcp.tool()
def list_events(date: str = "") -> list[dict]:
    """List scheduled calendar events. Optionally filter by date (YYYY-MM-DD)."""
    events = _load_events()
    if date:
        return [e for e in events if e["date"] == date]
    return events


@mcp.tool()
def delete_event(event_id: int) -> str:
    """Delete a calendar event by its numeric ID."""
    events = _load_events()
    updated = [e for e in events if e["id"] != event_id]
    if len(updated) == len(events):
        return f"No event found with ID {event_id}."
    _save_events(updated)
    return f"Deleted event #{event_id}."


if __name__ == "__main__":
    mcp.run()