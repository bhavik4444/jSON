"""Personal Finance MCP server: log expenses, set budgets, check what's left.

Data lives in a local SQLite file (finance.db) next to this script.
Runs as a stdio subprocess started by host.py. Never print to stdout here:
stdout carries the MCP protocol. Use stderr for logs.
"""
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastmcp import FastMCP

BASE = Path(__file__).parent
DB = Path(os.getenv("FINANCE_DB", BASE / "finance.db"))
TZ = ZoneInfo("Asia/Kolkata")

mcp = FastMCP(name="Finance")

PERIODS = {
    "today": "daily", "daily": "daily", "day": "daily",
    "week": "weekly", "weekly": "weekly",
    "month": "monthly", "monthly": "monthly",
}


def _log(msg: str) -> None:
    print(f"[finance-mcp] {msg}", file=sys.stderr, flush=True)


@contextmanager
def _db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init() -> None:
    with _db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT DEFAULT '',
                date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                period TEXT NOT NULL
            );
            """
        )


def _today() -> date:
    return datetime.now(TZ).date()


def _norm_period(period: str) -> str:
    p = PERIODS.get(period.strip().lower())
    if not p:
        raise ValueError("period must be one of: today/daily, week/weekly, month/monthly")
    return p


def _period_start(period: str) -> date:
    today = _today()
    if period == "daily":
        return today
    if period == "weekly":
        return today - timedelta(days=today.weekday())  # Monday
    return today.replace(day=1)


def _spent(con, category: str, period: str) -> float:
    row = con.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM expenses WHERE category = ? AND date BETWEEN ? AND ?",
        (category, _period_start(period).isoformat(), _today().isoformat()),
    ).fetchone()
    return row["s"]


def _inr(x: float) -> str:
    return f"₹{x:,.0f}" if float(x).is_integer() else f"₹{x:,.2f}"


def _status(con, category: str, budget: float, period: str) -> dict:
    spent = _spent(con, category, period)
    return {
        "category": category,
        "period": period,
        "budget": budget,
        "spent": spent,
        "remaining": budget - spent,
        "over_budget": spent > budget,
    }


@mcp.tool()
def add_expense(amount: float, category: str, note: str = "", date: str = "") -> str:
    """Log an expense. Amounts are in Indian rupees.
    Args:
        amount: Amount spent (e.g. 250).
        category: Short lowercase category such as food, transport, shopping, bills, entertainment.
                  Coffee, snacks and meals count as food.
        note: Optional detail (e.g. 'coffee at Starbucks').
        date: Optional date in YYYY-MM-DD format (defaults to today).
    """
    _log(f"add_expense({amount}, {category!r}, {note!r}, {date!r})")
    if amount <= 0:
        return "Amount must be greater than zero."
    category = category.strip().lower()
    day = date.strip() or _today().isoformat()
    day = datetime.fromisoformat(day).date().isoformat()  # validates the format
    with _db() as con:
        cur = con.execute(
            "INSERT INTO expenses (amount, category, note, date) VALUES (?, ?, ?, ?)",
            (amount, category, note, day),
        )
        msg = f"Logged {_inr(amount)} on {category} ({day}, id: {cur.lastrowid})."
        b = con.execute("SELECT amount, period FROM budgets WHERE category = ?", (category,)).fetchone()
        if b:
            s = _status(con, category, b["amount"], b["period"])
            if s["over_budget"]:
                msg += f" Over the {s['period']} {category} budget by {_inr(-s['remaining'])}."
            else:
                msg += f" {s['period'].capitalize()} {category} budget: {_inr(s['spent'])} spent, {_inr(s['remaining'])} left."
    return msg


@mcp.tool()
def list_expenses(limit: int = 10, category: str = "") -> list[dict]:
    """List recent expenses (newest first), each with its id.
    Args:
        limit: How many to return (default 10).
        category: Optional category filter.
    """
    _log(f"list_expenses({limit}, {category!r})")
    sql = "SELECT id, amount, category, note, date FROM expenses"
    params: list = []
    if category:
        sql += " WHERE category = ?"
        params.append(category.strip().lower())
    sql += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)
    with _db() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


@mcp.tool()
def delete_expense(expense_id: int) -> str:
    """Delete a logged expense by its id (get the id from list_expenses first)."""
    _log(f"delete_expense({expense_id})")
    with _db() as con:
        cur = con.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return f"Deleted expense {expense_id}." if cur.rowcount else f"No expense found with id {expense_id}."


@mcp.tool()
def get_spending_summary(period: str = "month") -> dict:
    """Total spending for a period, broken down by category.
    Args:
        period: 'today', 'week' or 'month' (default 'month').
    """
    _log(f"get_spending_summary({period!r})")
    p = _norm_period(period)
    start = _period_start(p).isoformat()
    with _db() as con:
        rows = con.execute(
            "SELECT category, SUM(amount) AS total FROM expenses WHERE date BETWEEN ? AND ? "
            "GROUP BY category ORDER BY total DESC",
            (start, _today().isoformat()),
        ).fetchall()
    by_cat = {r["category"]: r["total"] for r in rows}
    return {"period": p, "from": start, "total": sum(by_cat.values()), "by_category": by_cat}


@mcp.tool()
def set_budget(category: str, amount: float, period: str = "monthly") -> str:
    """Set (or replace) the spending budget for a category.
    Args:
        category: Category name, e.g. food.
        amount: Budget amount in rupees.
        period: 'daily', 'weekly' or 'monthly' (default 'monthly').
    """
    _log(f"set_budget({category!r}, {amount}, {period!r})")
    if amount <= 0:
        return "Budget must be greater than zero."
    category = category.strip().lower()
    p = _norm_period(period)
    with _db() as con:
        con.execute(
            "INSERT INTO budgets (category, amount, period) VALUES (?, ?, ?) "
            "ON CONFLICT(category) DO UPDATE SET amount = excluded.amount, period = excluded.period",
            (category, amount, p),
        )
    return f"Set {p} {category} budget to {_inr(amount)}."


@mcp.tool()
def get_budget_status(category: str = "") -> list[dict]:
    """How much of each budget is spent and how much is left for the current period.
    Args:
        category: Optional category; leave empty for all budgets.
    """
    _log(f"get_budget_status({category!r})")
    with _db() as con:
        if category:
            rows = con.execute(
                "SELECT category, amount, period FROM budgets WHERE category = ?",
                (category.strip().lower(),),
            ).fetchall()
        else:
            rows = con.execute("SELECT category, amount, period FROM budgets").fetchall()
        out = [_status(con, r["category"], r["amount"], r["period"]) for r in rows]
    return out or [{"message": "No budget set for that yet."}]


_init()

if __name__ == "__main__":
    mcp.run()