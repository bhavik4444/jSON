"""Todoist MCP server (free account, simple API token, no Google Cloud needed).

Runs as a stdio subprocess started by host.py. Never print to stdout here:
stdout carries the MCP protocol. Use stderr for logs.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")  # the server is a subprocess and doesn't get .env values automatically

API = "https://api.todoist.com/api/v1"
TZ_NAME = "Asia/Kolkata"  # should match the timezone set in your Todoist account settings
TZ = ZoneInfo(TZ_NAME)

mcp = FastMCP(name="Todoist")


def _log(msg: str) -> None:
    print(f"[todoist-mcp] {msg}", file=sys.stderr, flush=True)


def _call(method: str, path: str, **kwargs):
    """One place for all Todoist HTTP calls."""
    token = os.getenv("TODOIST_API_TOKEN")
    if not token:
        raise RuntimeError("TODOIST_API_TOKEN is missing. Add it to your .env file.")
    r = httpx.request(
        method, f"{API}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=15, **kwargs
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Todoist error {r.status_code}: {r.text[:200]}")
    return r.json() if r.content else {}


def _due_local(task: dict):
    """Existing due date/time of a task as a local datetime (or None)."""
    due = task.get("due")
    if not due:
        return None
    if due.get("datetime"):
        parsed = datetime.fromisoformat(due["datetime"].replace("Z", "+00:00"))
        return parsed.astimezone(TZ) if parsed.tzinfo else parsed.replace(tzinfo=TZ)
    if due.get("date"):
        return datetime.fromisoformat(due["date"]).replace(tzinfo=TZ)
    return None


def _due_str(task: dict) -> str:
    due = task.get("due")
    if not due:
        return ""
    if due.get("datetime"):
        return _due_local(task).strftime("%Y-%m-%d %H:%M")
    return due.get("date", "")


def _fmt(t: dict) -> dict:
    return {
        "id": t["id"],
        "content": t.get("content", ""),
        "due": _due_str(t),
        "priority": t.get("priority", 1),  # 1 = normal ... 4 = urgent
        "description": t.get("description", ""),
    }


def _due_fields(date: str, time: str, fallback_date: str = "") -> dict:
    """Turn date (YYYY-MM-DD) and time (HH:MM, local) into Todoist due fields."""
    if time:
        day = date or fallback_date or datetime.now(TZ).date().isoformat()
        local = datetime.fromisoformat(f"{day}T{time}").replace(tzinfo=TZ)
        return {"due_datetime": local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if date:
        return {"due_date": date}
    return {}


@mcp.tool()
def add_task(content: str, date: str = "", time: str = "", priority: int = 1, description: str = "") -> str:
    """Add a task or reminder to the user's Todoist.
    Args:
        content: The task text (e.g. 'Submit the deck').
        date: Optional due date in YYYY-MM-DD format.
        time: Optional due time in HH:MM 24-hour format (uses today if no date is given).
        priority: 1 = normal, 2 = medium, 3 = high, 4 = urgent.
        description: Optional extra notes.
    """
    _log(f"add_task({content!r}, {date!r}, {time!r}, p{priority})")
    body = {"content": content, "priority": priority, **_due_fields(date, time)}
    if description:
        body["description"] = description
    t = _call("POST", "/tasks", json=body)
    due = _due_str(t)
    return f"Added task '{content}'" + (f", due {due}" if due else "") + f" (id: {t['id']})."


@mcp.tool()
def list_tasks(filter: str = "") -> list[dict]:
    """List the user's active tasks, each with its id.
    Args:
        filter: Optional Todoist filter such as 'today', 'tomorrow', 'overdue', '7 days',
                'no date' or 'today | overdue'. Leave empty for all active tasks.
    """
    _log(f"list_tasks({filter!r})")
    if filter:
        data = _call("GET", "/tasks/filter", params={"query": filter, "limit": 50})
    else:
        data = _call("GET", "/tasks", params={"limit": 50})
    items = data["results"] if isinstance(data, dict) else data
    return [_fmt(t) for t in items]


@mcp.tool()
def update_task(task_id: str, content: str = "", date: str = "", time: str = "", priority: int = 0) -> str:
    """Rename or reschedule an existing task. Only pass the fields that change.
    Args:
        task_id: The id from list_tasks.
        content: New task text (optional).
        date: New due date YYYY-MM-DD (optional).
        time: New due time HH:MM, 24-hour (optional).
        priority: New priority 1-4 (optional, 0 = unchanged).
    """
    _log(f"update_task({task_id}, {content!r}, {date!r}, {time!r}, p{priority})")
    body = {}
    if content:
        body["content"] = content
    if priority:
        body["priority"] = priority
    if date or time:
        fallback = ""
        if time and not date:  # keep the task's existing day when only the time changes
            existing = _due_local(_call("GET", f"/tasks/{task_id}"))
            fallback = existing.date().isoformat() if existing else ""
        body.update(_due_fields(date, time, fallback))
    if not body:
        return "Nothing to change."
    t = _call("POST", f"/tasks/{task_id}", json=body)
    return f"Updated '{t.get('content', '')}', due {_due_str(t) or 'no date'}."


@mcp.tool()
def complete_task(task_id: str) -> str:
    """Mark a task as done (get the id from list_tasks first)."""
    _log(f"complete_task({task_id})")
    _call("POST", f"/tasks/{task_id}/close")
    return f"Marked task {task_id} as done."


@mcp.tool()
def delete_task(task_id: str) -> str:
    """Permanently delete a task (get the id from list_tasks first)."""
    _log(f"delete_task({task_id})")
    _call("DELETE", f"/tasks/{task_id}")
    return f"Deleted task {task_id}."


if __name__ == "__main__":
    mcp.run()