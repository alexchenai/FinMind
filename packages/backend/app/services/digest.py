"""
Smart weekly financial digest service.
Generates summaries highlighting spending trends, top categories,
budget performance, and actionable insights.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..extensions import db
from ..models import Bill, Expense, RecurringExpense


def _start_of_week(ref: datetime) -> datetime:
    """Monday 00:00:00 of the ISO week containing ref."""
    return (ref - timedelta(days=ref.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _week_range(offset: int = 0) -> Tuple[datetime, datetime]:
    """Return (start, end) for the ISO week shifted by offset weeks."""
    now = datetime.utcnow()
    start = _start_of_week(now) + timedelta(weeks=offset)
    end = start + timedelta(days=7)
    return start, end


def _expenses_in_range(user_id: int, start: datetime, end: datetime) -> List[Expense]:
    return Expense.query.filter(
        Expense.user_id == user_id,
        Expense.spent_at >= start.date(),
        Expense.spent_at < end.date(),
    ).all()


def generate_weekly_digest(user_id: int, week_offset: int = -1) -> Dict[str, Any]:
    """
    Generate a weekly financial digest for the given user.

    Parameters
    ----------
    user_id : int
    week_offset : int
        0 = current (possibly incomplete) week, -1 = last complete week.

    Returns
    -------
    dict with keys:
      - week_label, start_date, end_date
      - total_spent, total_income
      - top_categories (list)
      - daily_breakdown (dict: date -> amount)
      - week_over_week_change (pct)
      - biggest_expense (dict or None)
      - insight (str)
      - bills_due_next_week (list)
    """
    start, end = _week_range(week_offset)
    prev_start, prev_end = _week_range(week_offset - 1)

    expenses = _expenses_in_range(user_id, start, end)
    prev_expenses = _expenses_in_range(user_id, prev_start, prev_end)

    # Totals
    total_spent = float(sum(float(e.amount) for e in expenses if e.expense_type != "INCOME"))
    total_income = float(sum(float(e.amount) for e in expenses if e.expense_type == "INCOME"))
    prev_total = float(sum(float(e.amount) for e in prev_expenses if e.expense_type != "INCOME"))

    # Week-over-week
    wow_change = None
    if prev_total > 0:
        wow_change = round(((total_spent - prev_total) / prev_total) * 100, 1)

    # Category breakdown
    cat_totals: Dict[str, float] = defaultdict(float)
    for e in expenses:
        if e.expense_type != "INCOME":
            cat_name = e.category.name if e.category_id else "Uncategorised"
            cat_totals[cat_name] += float(e.amount)

    top_categories = sorted(
        [{"name": k, "amount": round(v, 2)} for k, v in cat_totals.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )[:5]

    # Daily breakdown
    daily: Dict[str, float] = defaultdict(float)
    for e in expenses:
        if e.expense_type != "INCOME":
            daily[str(e.spent_at)] += float(e.amount)
    daily_breakdown = {k: round(v, 2) for k, v in sorted(daily.items())}

    # Biggest single expense
    non_income = [e for e in expenses if e.expense_type != "INCOME"]
    biggest = None
    if non_income:
        be = max(non_income, key=lambda e: float(e.amount))
        biggest = {
            "notes": be.notes or "—",
            "amount": float(be.amount),
            "date": str(be.spent_at),
            "category": be.category.name if be.category_id else "Uncategorised",
        }

    # Insight text
    insight = _generate_insight(total_spent, prev_total, wow_change, top_categories)

    # Bills due next week
    next_start, next_end = _week_range(week_offset + 1)
    bills_due = Bill.query.filter(
        Bill.user_id == user_id,
        Bill.due_date >= next_start.date(),
        Bill.due_date < next_end.date(),
    ).all() if hasattr(Bill, "due_date") else []

    return {
        "week_label": f"Week of {start.strftime('%b %d, %Y')}",
        "start_date": start.date().isoformat(),
        "end_date": (end - timedelta(days=1)).date().isoformat(),
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "top_categories": top_categories,
        "daily_breakdown": daily_breakdown,
        "week_over_week_change": wow_change,
        "biggest_expense": biggest,
        "insight": insight,
        "bills_due_next_week": [
            {"name": b.name, "amount": float(b.amount), "due": str(b.due_date)}
            for b in bills_due
        ],
    }


def _generate_insight(total: float, prev_total: float, wow: Optional[float],
                       top_categories: List[Dict]) -> str:
    """Rule-based insight sentence from spending data."""
    if wow is None:
        return "Not enough history to compare weeks yet."

    parts: List[str] = []
    if wow > 20:
        parts.append(f"Spending jumped {abs(wow):.0f}% vs last week — consider reviewing discretionary items.")
    elif wow > 0:
        parts.append(f"Spending up {wow:.1f}% vs last week.")
    elif wow < -20:
        parts.append(f"Great job — spending down {abs(wow):.0f}% vs last week.")
    elif wow < 0:
        parts.append(f"Spending down {abs(wow):.1f}% vs last week.")
    else:
        parts.append("Spending on track compared to last week.")

    if top_categories:
        top = top_categories[0]
        parts.append(f"Biggest category: {top['name']} (${top['amount']:,.2f}).")

    return " ".join(parts)
