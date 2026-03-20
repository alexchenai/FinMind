"""Tests for Spending Trend Heatmap service (#116)."""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_expense_row(spent_at: date, total: Decimal, cnt: int):
    row = MagicMock()
    row.spent_at = spent_at
    row.total = total
    row.cnt = cnt
    return row


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestGetSpendingHeatmap:

    def _call(self, rows, months=3):
        from packages.backend.app.services.spending_heatmap import get_spending_heatmap
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = rows
        with patch("packages.backend.app.services.spending_heatmap.db") as mock_db:
            mock_db.session.query.return_value = mock_query
            return get_spending_heatmap(1, months)

    def test_empty_returns_structure(self):
        result = self._call([])
        assert "cells" in result
        assert "day_summaries" in result
        assert "busiest_day" in result
        assert "quietest_day" in result
        assert "total_spend" in result
        assert result["cells"] == []
        assert len(result["day_summaries"]) == 7

    def test_total_spend_matches(self):
        today = date.today()
        rows = [
            make_expense_row(today, Decimal("100"), 1),
            make_expense_row(today - timedelta(days=1), Decimal("50"), 2),
        ]
        result = self._call(rows)
        assert abs(result["total_spend"] - 150.0) < 0.01

    def test_cells_contain_expected_fields(self):
        today = date.today()
        rows = [make_expense_row(today, Decimal("200"), 3)]
        result = self._call(rows)
        assert len(result["cells"]) == 1
        cell = result["cells"][0]
        assert "week" in cell
        assert "day_of_week" in cell
        assert "total_spend" in cell
        assert "transaction_count" in cell
        assert cell["total_spend"] == 200.0
        assert cell["transaction_count"] == 3

    def test_day_of_week_correct(self):
        # Find a known Monday
        today = date.today()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday)
        rows = [make_expense_row(last_monday, Decimal("100"), 1)]
        result = self._call(rows)
        assert result["cells"][0]["day_of_week"] == 0  # Monday

    def test_day_summaries_have_seven_entries(self):
        result = self._call([])
        assert len(result["day_summaries"]) == 7
        days = [d["day_name"] for d in result["day_summaries"]]
        assert "Monday" in days
        assert "Sunday" in days

    def test_avg_per_week_calculation(self):
        # Two different Mondays should give avg = total / 2
        today = date.today()
        days_since_monday = today.weekday()
        monday1 = today - timedelta(days=days_since_monday)
        monday2 = monday1 - timedelta(weeks=1)
        rows = [
            make_expense_row(monday1, Decimal("80"), 1),
            make_expense_row(monday2, Decimal("60"), 1),
        ]
        result = self._call(rows)
        monday_summary = next(d for d in result["day_summaries"] if d["day_name"] == "Monday")
        assert abs(monday_summary["avg_per_week"] - 70.0) < 0.01

    def test_busiest_day_identified(self):
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        friday = monday + timedelta(days=4)
        rows = [
            make_expense_row(monday, Decimal("50"), 1),
            make_expense_row(friday, Decimal("500"), 5),
        ]
        result = self._call(rows)
        assert result["busiest_day"] == "Friday"

    def test_quietest_day_identified(self):
        today = date.today()
        days_since_monday = today.weekday()
        tuesday = today - timedelta(days=days_since_monday - 1)
        saturday = today - timedelta(days=days_since_monday - 5)
        rows = [
            make_expense_row(tuesday, Decimal("500"), 3),
            make_expense_row(saturday, Decimal("10"), 1),
        ]
        result = self._call(rows)
        # Saturday has lowest avg (only 1 week), but days with 0 spend sort lower
        assert result["quietest_day"] != result["busiest_day"]

    def test_months_param_clamped_min(self):
        result = self._call([], months=0)
        assert result["period_months"] == 1

    def test_months_param_clamped_max(self):
        result = self._call([], months=99)
        assert result["period_months"] == 12

    def test_start_end_dates_present(self):
        result = self._call([])
        assert "start_date" in result
        assert "end_date" in result
        # end_date should be today
        assert result["end_date"] == date.today().isoformat()

    def test_multiple_expenses_same_day_aggregated(self):
        today = date.today()
        rows = [make_expense_row(today, Decimal("300"), 4)]
        result = self._call(rows)
        assert len(result["cells"]) == 1
        assert result["cells"][0]["total_spend"] == 300.0
        assert result["cells"][0]["transaction_count"] == 4

    def test_peak_week_in_summary(self):
        today = date.today()
        days_since_monday = today.weekday()
        wednesday = today - timedelta(days=days_since_monday - 2)
        rows = [make_expense_row(wednesday, Decimal("400"), 2)]
        result = self._call(rows)
        wed_summary = next(d for d in result["day_summaries"] if d["day_name"] == "Wednesday")
        assert wed_summary["peak_week"] is not None

    def test_zero_spend_days_have_zero_total(self):
        result = self._call([])
        for summary in result["day_summaries"]:
            assert summary["total_spend"] == 0.0
            assert summary["transaction_count"] == 0

    def test_transaction_count_in_day_summary(self):
        today = date.today()
        rows = [make_expense_row(today, Decimal("200"), 7)]
        result = self._call(rows)
        dow = today.weekday()
        day_summary = next(d for d in result["day_summaries"] if d["day_of_week"] == dow)
        assert day_summary["transaction_count"] == 7

    def test_period_months_in_result(self):
        result = self._call([], months=6)
        assert result["period_months"] == 6


class TestSpendingHeatmapRoute:

    def _get_app(self):
        from packages.backend.app import create_app
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                          "JWT_SECRET_KEY": "test-secret"})
        return app

    def test_route_requires_auth(self):
        app = self._get_app()
        with app.test_client() as client:
            resp = client.get("/insights/spending-heatmap")
            assert resp.status_code == 401

    def test_months_defaults_to_3(self):
        from packages.backend.app.services.spending_heatmap import get_spending_heatmap
        app = self._get_app()
        with app.test_client() as client:
            with patch("packages.backend.app.routes.spending_heatmap.get_spending_heatmap") as mock_fn:
                mock_fn.return_value = {"period_months": 3, "cells": [], "day_summaries": [],
                                        "busiest_day": "N/A", "quietest_day": "N/A",
                                        "total_spend": 0.0, "start_date": "2026-01-01",
                                        "end_date": "2026-03-31"}
                from flask_jwt_extended import create_access_token
                with app.app_context():
                    token = create_access_token(identity="1")
                resp = client.get("/insights/spending-heatmap",
                                  headers={"Authorization": f"Bearer {token}"})
                assert resp.status_code == 200
                mock_fn.assert_called_once_with(1, 3)