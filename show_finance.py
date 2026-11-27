"""Live finance view for the demo. Run in a second terminal: python show_finance.py
Refreshes every 2 seconds so the audience can watch rows appear as you chat."""
import os
import time

from finance_server import _db, _spent, _inr


def render() -> None:
    with _db() as con:
        print("=== BUDGETS ===")
        budgets = con.execute("SELECT category, amount, period FROM budgets").fetchall()
        if not budgets:
            print("(none set)")
        for b in budgets:
            spent = _spent(con, b["category"], b["period"])
            left = b["amount"] - spent
            flag = "  OVER!" if left < 0 else ""
            print(f"{b['category']:<14}{b['period']:<9}budget {_inr(b['amount']):>8}   "
                  f"spent {_inr(spent):>8}   left {_inr(left):>8}{flag}")
        print("\n=== RECENT EXPENSES ===")
        for r in con.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC LIMIT 10"):
            print(f"#{r['id']:<4}{r['date']}  {_inr(r['amount']):>8}  {r['category']:<12}{r['note']}")


if __name__ == "__main__":
    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            render()
            print("\n(refreshing every 2s, Ctrl+C to quit)")
            time.sleep(2)
    except KeyboardInterrupt:
        pass