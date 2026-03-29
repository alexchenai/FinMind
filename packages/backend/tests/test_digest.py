"""Tests for the smart weekly digest service."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

from app.services.digest import (
    _calculate_backoff,
    _generate_insight,
    _start_of_week,
    _week_range,
    generate_weekly_digest,
)


class TestStartOfWeek:
    def test_monday_returns_itself(self):
        monday = datetime(2026, 3, 23, 10, 30)  # Monday
        result = _start_of_week(monday)
        assert result.weekday() == 0
        assert result.hour == 0
        assert result.minute == 0

    def test_wednesday_returns_monday(self):
        wednesday = datetime(2026, 3, 25, 12, 0)  # Wednesday
        result = _start_of_week(wednesday)
        assert result.weekday() == 0
        assert result.day == 23  # Monday Mar 23

    def test_sunday_returns_correct_monday(self):
        sunday = datetime(2026, 3, 29, 23, 0)  # Sunday
        result = _start_of_week(sunday)
        assert result.weekday() == 0


class TestWeekRange:
    def test_current_week_ends_7_days_later(self):
        start, end = _week_range(0)
        assert (end - start).days == 7

    def test_last_week_offset_minus_one(self):
        start_current, _ = _week_range(0)
        start_last, end_last = _week_range(-1)
        assert start_last == start_current - timedelta(weeks=1)
        assert end_last == start_current


class TestGenerateInsight:
    def test_no_prior_data(self):
        insight = _generate_insight(100, 0, None, [])
        assert "enough history" in insight.lower()

    def test_spending_up_large(self):
        insight = _generate_insight(1200, 1000, 20.1, [{"name": "Food", "amount": 500}])
        assert "jumped" in insight.lower() or "up" in insight.lower()

    def test_spending_down_large(self):
        insight = _generate_insight(800, 1000, -20.5, [])
        assert "down" in insight.lower()

    def test_top_category_included(self):
        insight = _generate_insight(900, 1000, -10.0, [{"name": "Housing", "amount": 450}])
        assert "Housing" in insight

    def test_flat_spending(self):
        insight = _generate_insight(1000, 1000, 0.0, [])
        assert "track" in insight.lower() or "flat" in insight.lower()


class TestGenerateWeeklyDigest:
    @patch("app.services.digest._expenses_in_range")
    @patch("app.services.digest.Bill")
    def test_returns_required_keys(self, mock_bill, mock_expenses):
        mock_expenses.return_value = []
        mock_bill.query.filter.return_value.all.return_value = []
        digest = generate_weekly_digest(user_id=1)
        required_keys = [
            "week_label", "start_date", "end_date", "total_spent",
            "total_income", "top_categories", "daily_breakdown",
            "week_over_week_change", "biggest_expense", "insight",
            "bills_due_next_week",
        ]
        for key in required_keys:
            assert key in digest, f"Missing key: {key}"

    @patch("app.services.digest._expenses_in_range")
    @patch("app.services.digest.Bill")
    def test_empty_week_totals_zero(self, mock_bill, mock_expenses):
        mock_expenses.return_value = []
        mock_bill.query.filter.return_value.all.return_value = []
        digest = generate_weekly_digest(user_id=1)
        assert digest["total_spent"] == 0.0
        assert digest["total_income"] == 0.0
        assert digest["top_categories"] == []
        assert digest["biggest_expense"] is None

    @patch("app.services.digest._expenses_in_range")
    @patch("app.services.digest.Bill")
    def test_week_over_week_none_when_prev_empty(self, mock_bill, mock_expenses):
        # Return empty for both weeks
        mock_expenses.return_value = []
        mock_bill.query.filter.return_value.all.return_value = []
        digest = generate_weekly_digest(user_id=1)
        assert digest["week_over_week_change"] is None


class TestDigestEndpoint:
    def test_digest_requires_auth(self, client):
        resp = client.get("/api/digest")
        assert resp.status_code == 401

    def test_invalid_week_offset(self, auth_client):
        resp = auth_client.get("/api/digest?week_offset=1")
        assert resp.status_code == 400

    def test_non_integer_offset_rejected(self, auth_client):
        resp = auth_client.get("/api/digest?week_offset=foo")
        assert resp.status_code == 400

    @patch("app.routes.digest.generate_weekly_digest")
    def test_digest_returns_json(self, mock_gen, auth_client):
        mock_gen.return_value = {
            "week_label": "Week of Mar 24",
            "start_date": "2026-03-24",
            "end_date": "2026-03-30",
            "total_spent": 500.0,
            "total_income": 2000.0,
            "top_categories": [],
            "daily_breakdown": {},
            "week_over_week_change": None,
            "biggest_expense": None,
            "insight": "test",
            "bills_due_next_week": [],
        }
        resp = auth_client.get("/api/digest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_spent"] == 500.0
