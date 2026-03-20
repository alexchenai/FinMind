"""Route: GET /insights/spending-heatmap — Spending Trend Heatmap (#116)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.spending_heatmap import get_spending_heatmap

bp = Blueprint("spending_heatmap", __name__)


@bp.get("/spending-heatmap")
@jwt_required()
def spending_heatmap():
    """Return a day-of-week x week spending heatmap for the authenticated user.

    Query params:
      months (int, optional): Number of months to analyse (1-12). Defaults to 3.

    Returns 200 with:
      {
        "period_months": int,
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "cells": [
          { "week": int, "day_of_week": int, "total_spend": float,
            "transaction_count": int },
          ...
        ],
        "day_summaries": [
          { "day_of_week": int, "day_name": str, "total_spend": float,
            "avg_per_week": float, "transaction_count": int,
            "peak_week": int | null },
          ...
        ],
        "busiest_day": str,
        "quietest_day": str,
        "total_spend": float
      }
    """
    uid = int(get_jwt_identity())
    try:
        months = int(request.args.get("months", 3))
    except (ValueError, TypeError):
        months = 3

    result = get_spending_heatmap(uid, months)
    return jsonify(result), 200