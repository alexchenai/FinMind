"""
REST endpoint for weekly financial digest.
GET /api/digest?week_offset=-1   (default: last complete week)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.digest import generate_weekly_digest

digest_bp = Blueprint("digest", __name__, url_prefix="/api/digest")


@digest_bp.get("")
@jwt_required()
def get_digest():
    """
    Return the weekly financial digest for the authenticated user.

    Query params:
      week_offset (int, default -1): 0 = current week, -1 = last week, -2 = two weeks ago.
    """
    user_id = int(get_jwt_identity())
    try:
        offset = int(request.args.get("week_offset", -1))
    except (TypeError, ValueError):
        return jsonify({"error": "week_offset must be an integer"}), 400

    if offset > 0:
        return jsonify({"error": "week_offset must be 0 or negative (past weeks only)"}), 400

    digest = generate_weekly_digest(user_id=user_id, week_offset=offset)
    return jsonify(digest)
