"""
Spending Trend Heatmap — FinMind (#116)

Aggregates spending data into a day-of-week x week-number matrix,
enabling visualization of spending patterns over time. Returns both
a raw heatmap grid and per-day-of-week summary statistics.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import func, extract

from ..extensions import db
from ..models import Category, Expense

logger = logging.getLogger("finmind.spending_heatmap")

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class DaySummary(TypedDict):
    day_of_week: int       # 0=Monday, 6=Sunday
    day_name: str
    total_spend: float
    avg_per_week: float
    transaction_count: int
    peak_week: int | None  # ISO week number with highest spend


class HeatmapCell(TypedDict):
    week: int              # ISO week number (1-53)
    day_of_week: int       # 0=Monday, 6=Sunday
    total_spend: float
    transaction_count: int


class HeatmapResult(TypedDict):
    period_months: int
    start_date: str
    end_date: str
    cells: list[HeatmapCell]
    day_summaries: list[DaySummary]
    busiest_day: str        # day name with highest average spend
    quietest_day: str       # day name with lowest average spend
    total_spend: float


def get_spending_heatmap(user_id: int, months: int = 3) -> HeatmapResult:
    """Generate a spending heatmap for the given user.

    Args:
        user_id: Authenticated user ID.
        months: Number of months to look back (1-12). Defaults to 3.

    Returns:
        HeatmapResult with grid cells and day-of-week summaries.
    """
    months = max(1, min(12, months))

    end_date = date.today()
    start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 1):
        start_date = (start_date - timedelta(days=1)).replace(day=1)

    logger.info(
        "Computing heatmap user=%s period=%s to %s",
        user_id, start_date, end_date,
    )

    # Query expenses in range (EXPENSE type only, exclude INCOME)
    expenses = (
        db.session.query(
            Expense.spent_at,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("cnt"),
        )
        .filter(
            Expense.user_id == user_id,
            Expense.expense_type == "EXPENSE",
            Expense.spent_at >= start_date,
            Expense.spent_at <= end_date,
        )
        .group_by(Expense.spent_at)
        .all()
    )

    # Build (week, dow) -> (total, count) map
    cell_map: dict[tuple[int, int], tuple[Decimal, int]] = {}
    for row in expenses:
        spent: date = row.spent_at
        dow = spent.weekday()      # 0=Monday
        week = spent.isocalendar()[1]  # ISO week
        key = (week, dow)
        prev_total, prev_cnt = cell_map.get(key, (Decimal("0"), 0))
        cell_map[key] = (prev_total + row.total, prev_cnt + row.cnt)

    # Build cells list
    cells: list[HeatmapCell] = []
    for (week, dow), (total, cnt) in sorted(cell_map.items()):
        cells.append(
            HeatmapCell(
                week=week,
                day_of_week=dow,
                total_spend=float(total),
                transaction_count=cnt,
            )
        )

    # Build per-day summaries
    day_totals: dict[int, Decimal] = {d: Decimal("0") for d in range(7)}
    day_counts: dict[int, int] = {d: 0 for d in range(7)}
    day_weeks: dict[int, set[int]] = {d: set() for d in range(7)}
    day_peak_spend: dict[int, Decimal] = {d: Decimal("0") for d in range(7)}
    day_peak_week: dict[int, int | None] = {d: None for d in range(7)}

    for (week, dow), (total, cnt) in cell_map.items():
        day_totals[dow] += total
        day_counts[dow] += cnt
        day_weeks[dow].add(week)
        if total > day_peak_spend[dow]:
            day_peak_spend[dow] = total
            day_peak_week[dow] = week

    day_summaries: list[DaySummary] = []
    for dow in range(7):
        week_count = len(day_weeks[dow]) or 1
        day_summaries.append(
            DaySummary(
                day_of_week=dow,
                day_name=DAY_NAMES[dow],
                total_spend=float(day_totals[dow]),
                avg_per_week=float(day_totals[dow] / week_count),
                transaction_count=day_counts[dow],
                peak_week=day_peak_week[dow],
            )
        )

    # Identify busiest and quietest days (by avg spend)
    sorted_days = sorted(day_summaries, key=lambda d: d["avg_per_week"], reverse=True)
    busiest = sorted_days[0]["day_name"] if sorted_days else "N/A"
    quietest = sorted_days[-1]["day_name"] if sorted_days else "N/A"

    total_spend = float(sum(day_totals.values()))

    return HeatmapResult(
        period_months=months,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        cells=cells,
        day_summaries=day_summaries,
        busiest_day=busiest,
        quietest_day=quietest,
        total_spend=total_spend,
    )